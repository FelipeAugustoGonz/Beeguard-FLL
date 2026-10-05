# BeeGuard AI — coleta de áudio

Guia para executar no PC a coleta de áudio do INMP441 usando um ESP32 e USB/Serial.

## 1. Ligações

| INMP441 | ESP32 |
| --- | --- |
| SCK / BCLK | GPIO 26 |
| WS / LRC | GPIO 25 |
| SD / DOUT | GPIO 33 |
| VDD | 3V3 |
| GND | GND |
| L/R | GND (seleciona canal esquerdo) |

Use **3V3** para alimentar o microfone e conecte **L/R ao GND**, pois o sketch lê o canal esquerdo do I2S.

## 2. Preparar o ESP32

1. Abra `BeeGuardAI.ino` no Arduino IDE.
2. Selecione a placa ESP32 e a porta USB em **Ferramentas → Porta**.
3. Instale a biblioteca **arduinoFFT** pelo Gerenciador de Bibliotecas, caso ainda não esteja instalada.
4. Envie o sketch para o ESP32.

O sketch captura áudio mono a 16000 Hz e transmite gravações de 10 segundos como PCM de 16 bits. As capturas são consecutivas, com um intervalo aproximado de 1 segundo. Ele também calcula e mostra os indicadores de áudio após cada gravação.

## 3. Preparar o coletor Python

Abra um terminal nesta pasta e instale a dependência:

```powershell
python -m pip install pyserial
```

No início de `capture_audio.py`, ajuste `SERIAL_PORT` para a porta do ESP32, por exemplo:

```python
SERIAL_PORT = "COM4"
```

Para descobrir a porta, veja **Ferramentas → Porta** no Arduino IDE ou **Gerenciador de Dispositivos → Portas (COM e LPT)** no Windows. Feche o Serial Monitor antes de rodar o coletor, pois ele ocupa a mesma porta.

## 4. Gravar

Conecte o ESP32 ao PC por USB e execute:

```powershell
python capture_audio.py
```

O programa aguardará o ESP32 e salvará cada gravação completa na pasta `recordings/`, criando-a automaticamente. Os nomes começam em `recording_001.wav` e avançam sem sobrescrever arquivos existentes. Ao salvar, o coletor também informa sample rate, duração, quantidade de samples e amplitudes mínima e máxima.

Para parar, pressione **Ctrl+C**. Uma transmissão interrompida não é salva como WAV completo; gravações anteriores permanecem intactas.

## 5. Conferir o WAV

Abra um arquivo `recordings/recording_001.wav` no Audacity ou em outro reprodutor. O formato esperado é:

- WAV PCM, 16 bits;
- mono, 16000 Hz;
- 160000 samples e aproximadamente 10 segundos por gravação.

## 6. Gerar espectrogramas

Depois de confirmar que existem WAVs válidos em `recordings/`, instale as bibliotecas necessárias:

```powershell
python -m pip install numpy scipy matplotlib
```

Execute na pasta do projeto:

```powershell
python generate_spectrograms.py
```

O script lê cada WAV PCM 16-bit mono a 16000 Hz de `recordings/` e salva uma imagem PNG por áudio na pasta `spectrograms/`, por exemplo `recording_001_spectrogram.png`. Os WAVs originais não são alterados. Se não houver gravações, o script avisa; se algum arquivo não for válido ou estiver ilegível, informa o erro e continua com os demais.

### Como testar

1. Grave ao menos um áudio com `capture_audio.py` ou coloque um WAV válido no formato esperado dentro de `recordings/`.
2. Rode `python generate_spectrograms.py`.
3. Confirme a mensagem `OK` no terminal e abra o PNG correspondente dentro de `spectrograms/`.
4. O gráfico deve mostrar tempo no eixo horizontal, frequência (0 a 8000 Hz) no vertical e a potência do sinal em cores.

Se a pasta ainda estiver vazia, rode o script mesmo assim: ele deve informar que não encontrou WAVs e terminar sem erro.

## Fluxo dos dados

**INMP441 → I2S → ESP32 → USB Serial binária → `capture_audio.py` → arquivos WAV → `generate_spectrograms.py` → imagens PNG**

O ESP32 enquadra cada áudio com cabeçalho contendo a quantidade de samples e um marcador final. O Python usa esses dados para identificar e salvar cada gravação completa.
