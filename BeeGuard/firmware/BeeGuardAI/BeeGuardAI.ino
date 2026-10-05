#include <driver/i2s.h>
#include <arduinoFFT.h>
#include <math.h>

#define I2S_WS   25
#define I2S_SD   33
#define I2S_SCK  26

#define SAMPLE_RATE 16000
#define SAMPLES 1024
#define RECORD_SECONDS 10

// Protocolo: "BGAR" + versão (1) + uint32 LE samples + PCM16 LE + "BEND".
const uint8_t FRAME_MAGIC[5] = {'B','G','A','R',1};
const uint8_t FRAME_END[4] = {'B','E','N','D'};
const uint32_t RECORD_SAMPLES = SAMPLE_RATE * RECORD_SECONDS;

double vReal[SAMPLES];
double vImag[SAMPLES];
ArduinoFFT<double> FFT(vReal, vImag, SAMPLES, SAMPLE_RATE);

float rms = 0, pico = 0, freqDominante = 0;
float atividade = 0, energia = 0, estabilidade = 0, diversidade = 0;
float intensidadeDB = 0, iba = 0, saude = 0, ultimoRMS = 0;
int32_t sampleBuffer[SAMPLES];
int16_t pcmBuffer[SAMPLES];

void setupI2S() {
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 256,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };
  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK, .ws_io_num = I2S_WS,
    .data_out_num = I2S_PIN_NO_CHANGE, .data_in_num = I2S_SD
  };
  i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &pin_config);
}

// Captura n samples e mantém RMS/pico/arrays FFT da janela (preenchida com zero no fim).
bool capturarAudio(size_t n) {
  size_t bytesRead = 0;
  const size_t wanted = n * sizeof(int32_t);
  uint8_t *dst = reinterpret_cast<uint8_t *>(sampleBuffer);
  size_t total = 0;
  while (total < wanted) {
    size_t got = 0;
    esp_err_t err = i2s_read(I2S_NUM_0, dst + total, wanted - total, &got, portMAX_DELAY);
    if (err != ESP_OK || got == 0) return false;
    total += got;
  }
  bytesRead = total;
  (void)bytesRead;

  double soma = 0;
  pico = 0;
  for (size_t i = 0; i < SAMPLES; i++) {
    double valor = 0;
    if (i < n) {
      // INMP441 24-bit data is left-aligned in the 32-bit I2S slot.
      int32_t signedPcm = sampleBuffer[i] >> 16;
      pcmBuffer[i] = (int16_t)signedPcm;
      valor = signedPcm / 32768.0;
    } else {
      pcmBuffer[i] = 0;
    }
    vReal[i] = valor;
    vImag[i] = 0;
    soma += valor * valor;
    if (fabs(valor) > pico) pico = fabs(valor);
  }
  rms = sqrt(soma / SAMPLES);
  return true;
}

void processarFFT() {
  FFT.windowing(FFTWindow::Hamming, FFTDirection::Forward);
  FFT.compute(FFTDirection::Forward);
  FFT.complexToMagnitude();
  double maior = 0;
  int indiceMaior = 0, frequenciasAtivas = 0;
  for (int i = 1; i < SAMPLES / 2; i++) {
    if (vReal[i] > maior) { maior = vReal[i]; indiceMaior = i; }
    if (vReal[i] > 5) frequenciasAtivas++;
  }
  freqDominante = (indiceMaior * SAMPLE_RATE) / SAMPLES;
  diversidade = constrain((frequenciasAtivas * 100.0) / (SAMPLES / 2), 0, 100);
}

void calcularIndicadores() {
  intensidadeDB = constrain(20 * log10(rms + 0.000001) + 90, 0, 100);
  atividade = constrain(rms * 1500, 0, 100);
  energia = constrain(pico * 100, 0, 100);
  estabilidade = constrain(100 - (fabs(rms - ultimoRMS) * 1000), 0, 100);
  ultimoRMS = rms;
  iba = constrain((atividade + estabilidade + diversidade + energia) / 4.0, 0, 100);
  saude = (atividade + estabilidade + diversidade + iba) / 4.0;
}

void mostrarIndicadores() {
  Serial.println("\n==========================================");
  Serial.println("BEEGUARD AI");
  Serial.println("==========================================");
  Serial.printf("Intensidade: %.1f dB | RMS: %.5f | Pico: %.5f\n", intensidadeDB, rms, pico);
  Serial.printf("Frequencia dominante: %.1f Hz | Diversidade: %.1f %%\n", freqDominante, diversidade);
  Serial.printf("Atividade: %.1f %% | Energia: %.1f %% | Estabilidade: %.1f %%\n", atividade, energia, estabilidade);
  Serial.printf("IBA: %.1f | Saude da colmeia: %.1f %%\n", iba, saude);
  Serial.println(saude > 70 ? "STATUS: SAUDAVEL" : saude > 40 ? "STATUS: ATENCAO" : "STATUS: ALERTA");
  Serial.println("==========================================");
}

void enviarHeader(uint32_t count) {
  Serial.write(FRAME_MAGIC, sizeof(FRAME_MAGIC));
  uint8_t n[4] = {(uint8_t)count, (uint8_t)(count >> 8), (uint8_t)(count >> 16), (uint8_t)(count >> 24)};
  Serial.write(n, sizeof(n));
}

void gravarAudio() {
  enviarHeader(RECORD_SAMPLES);
  uint32_t remaining = RECORD_SAMPLES;
  while (remaining > 0) {
    size_t n = remaining < SAMPLES ? remaining : SAMPLES;
    if (!capturarAudio(n)) return; // Sem END: o coletor descarta este frame incompleto.
    // Little-endian PCM explícito, independente da ordem de bytes do ESP32.
    for (size_t i = 0; i < n; i++) {
      uint16_t u = (uint16_t)pcmBuffer[i];
      Serial.write((uint8_t)(u & 0xff));
      Serial.write((uint8_t)(u >> 8));
    }
    remaining -= n;
    if (n == SAMPLES) {
      processarFFT();
      calcularIndicadores();
    }
  }
  Serial.write(FRAME_END, sizeof(FRAME_END));
  Serial.flush();
  mostrarIndicadores(); // Texto apenas fora dos frames binários.
}

void setup() {
  Serial.begin(921600);
  setupI2S();
  delay(500);
  Serial.println("BeeGuard AI pronto; protocolo PCM16 ativo");
}

void loop() {
  gravarAudio();
  delay(1000); // Intervalo entre capturas consecutivas.
}
