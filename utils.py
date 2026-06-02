import json
import pyaudio
import wave
import threading
from datetime import datetime
import mido
import time

def configurar_audio():
    """
    Configura um dispositivo de captura de áudio via terminal.

    Fluxo:
    1. Lista dispositivos de entrada.
    2. Usuário escolhe o dispositivo.
    3. Usuário escolhe a quantidade de canais.
    4. Detecta sample rates suportados.
    5. Usuário escolhe o sample rate.
    6. Usuário escolhe o sample format.
    7. Usuário escolhe o chunk size.
    8. Retorna um dicionário JSON-ready.
    """

    pa = pyaudio.PyAudio()

    try:

        # ==================================================
        # LISTAR DISPOSITIVOS DE ENTRADA
        # ==================================================

        dispositivos = []

        print("\n" + "=" * 60)
        print("DISPOSITIVOS DE ENTRADA DISPONÍVEIS")
        print("=" * 60)

        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)

            if info["maxInputChannels"] > 0:
                dispositivos.append(i)

                print(
                    f"[{i}] {info['name']} "
                    f"(Máx canais: {int(info['maxInputChannels'])})"
                )

        if not dispositivos:
            raise RuntimeError(
                "Nenhum dispositivo de entrada encontrado."
            )

        # ==================================================
        # ESCOLHER DISPOSITIVO
        # ==================================================

        while True:
            try:
                device_index = int(
                    input(
                        "\nDigite o índice do dispositivo desejado: "
                    )
                )

                if device_index not in dispositivos:
                    raise ValueError

                break

            except ValueError:
                print("Índice inválido.")

        device_info = pa.get_device_info_by_index(device_index)

        print("\nDispositivo selecionado:")
        print(f"Nome: {device_info['name']}")

        # ==================================================
        # ESCOLHER CANAIS
        # ==================================================

        max_channels = int(device_info["maxInputChannels"])

        print(
            f"\nNúmero máximo de canais suportados: "
            f"{max_channels}"
        )

        while True:
            try:
                channels = int(
                    input(
                        f"Escolha a quantidade de canais "
                        f"(1-{max_channels}): "
                    )
                )

                if 1 <= channels <= max_channels:
                    break

                raise ValueError

            except ValueError:
                print("Quantidade inválida.")

        # ==================================================
        # DETECTAR SAMPLE RATES SUPORTADOS
        # ==================================================

        print("\nVerificando sample rates suportados...")

        sample_rates_teste = [
            8000,
            11025,
            16000,
            22050,
            32000,
            44100,
            48000,
            88200,
            96000,
            192000
        ]

        rates_suportados = []

        for rate in sample_rates_teste:
            try:
                if pa.is_format_supported(
                    rate,
                    input_device=device_index,
                    input_channels=channels,
                    input_format=pyaudio.paInt16
                ):
                    rates_suportados.append(rate)

            except ValueError:
                pass

        if not rates_suportados:
            raise RuntimeError(
                "Nenhum sample rate compatível encontrado."
            )

        print("\nSample rates suportados:")

        for idx, rate in enumerate(rates_suportados):
            print(f"[{idx}] {rate} Hz")

        while True:
            try:
                rate_idx = int(
                    input(
                        "\nEscolha o índice do sample rate: "
                    )
                )

                sample_rate = rates_suportados[rate_idx]
                break

            except (ValueError, IndexError):
                print("Opção inválida.")

        # ==================================================
        # ESCOLHER SAMPLE FORMAT
        # ==================================================

        formatos = {
            1: ("paInt16", pyaudio.paInt16),
            2: ("paInt24", pyaudio.paInt24),
            3: ("paInt32", pyaudio.paInt32),
            4: ("paFloat32", pyaudio.paFloat32),
            5: ("paUInt8", pyaudio.paUInt8)
        }

        print("\n" + "=" * 60)
        print("FORMATOS DISPONÍVEIS")
        print("=" * 60)

        for idx, (nome, _) in formatos.items():
            print(f"[{idx}] {nome}")

        while True:

            try:
                formato_idx = int(
                    input(
                        "\nEscolha o formato de amostra: "
                    )
                )

                if formato_idx not in formatos:
                    raise ValueError

                sample_format_name, sample_format = (
                    formatos[formato_idx]
                )

                pa.is_format_supported(
                    sample_rate,
                    input_device=device_index,
                    input_channels=channels,
                    input_format=sample_format
                )

                break

            except ValueError:
                print(
                    "Formato não suportado para "
                    "essa configuração."
                )

        # ==================================================
        # ESCOLHER CHUNK SIZE
        # ==================================================

        chunks = [
            128,
            256,
            512,
            1024,
            2048,
            4096,
            8192
        ]

        print("\n" + "=" * 60)
        print("CHUNK SIZES")
        print("=" * 60)

        for idx, chunk in enumerate(chunks):

            latencia_ms = (
                chunk / sample_rate
            ) * 1000

            print(
                f"[{idx}] "
                f"{chunk:<5} "
                f"(latência ~ {latencia_ms:.2f} ms)"
            )

        print(f"[{len(chunks)}] Valor personalizado")

        while True:

            try:
                opcao = int(
                    input(
                        "\nEscolha o chunk size: "
                    )
                )

                if opcao == len(chunks):

                    chunk_size = int(
                        input(
                            "Digite o chunk size desejado: "
                        )
                    )

                    if chunk_size <= 0:
                        raise ValueError

                else:
                    chunk_size = chunks[opcao]

                break

            except (ValueError, IndexError):
                print("Valor inválido.")

        # ==================================================
        # MONTAR CONFIGURAÇÃO
        # ==================================================

        config = {
            "audio": {
                "device_index": device_index,
                "device_name": device_info["name"],
                "channels": channels,
                "sample_rate": sample_rate,
                "sample_format": sample_format_name,
                "chunk_size": chunk_size
            }
        }

        # ==================================================
        # EXIBIR RESULTADO
        # ==================================================

        print("\n" + "=" * 60)
        print("CONFIGURAÇÃO SELECIONADA")
        print("=" * 60)

        print(
            json.dumps(
                config,
                indent=4,
                ensure_ascii=False
            )
        )

        return config

    finally:
        pa.terminate()

def gravar_audio(config, output_file=None):
    """
    Grava áudio usando a configuração gerada anteriormente.

    Args:
        config (dict): JSON de configuração.
        output_file (str): Caminho do WAV. Se None, gera nome automático.
    """

    audio_cfg = config["audio"]

    formato = getattr(
        pyaudio,
        audio_cfg["sample_format"]
    )

    channels = audio_cfg["channels"]
    sample_rate = audio_cfg["sample_rate"]
    chunk_size = audio_cfg["chunk_size"]
    device_index = audio_cfg["device_index"]

    pa = pyaudio.PyAudio()

    stream = pa.open(
        format=formato,
        channels=channels,
        rate=sample_rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=chunk_size
    )

    if output_file is None:
        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        output_file = f"gravacao_{timestamp}.wav"

    frames = []
    stop_event = threading.Event()

    print("\nPressione ENTER para iniciar a gravação...")
    input()

    print("Gravando...")
    print("Pressione ENTER novamente para finalizar.")

    def aguardar_parada():
        input()
        stop_event.set()

    threading.Thread(
        target=aguardar_parada,
        daemon=True
    ).start()

    try:

        while not stop_event.is_set():

            data = stream.read(
                chunk_size,
                exception_on_overflow=False
            )

            frames.append(data)

    finally:

        print("\nFinalizando gravação...")

        stream.stop_stream()
        stream.close()

        sample_width = pa.get_sample_size(formato)

        pa.terminate()
        print("channels =", channels)
        print("sample_rate =", sample_rate)
        print("sample_format =", audio_cfg["sample_format"])
        print("sample_width =", sample_width)
        print("frames =", len(frames))
        with wave.open(output_file, "wb") as wf:

            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)

            wf.writeframes(
                b"".join(frames)
            )

        print(f"Arquivo salvo: {output_file}")

    return output_file

def configurar_midi():
    """
    Configuração interativa de dispositivos MIDI.

    Retorna:
        dict
    """

    print("\n" + "=" * 60)
    print("DISPOSITIVOS MIDI DE ENTRADA")
    print("=" * 60)

    portas = mido.get_input_names()

    if not portas:
        raise RuntimeError(
            "Nenhuma entrada MIDI encontrada."
        )

    for idx, porta in enumerate(portas):
        print(f"[{idx}] {porta}")

    print("\nVocê pode selecionar uma ou mais portas.")
    print("Exemplo: 0")
    print("Exemplo: 0,2,3")

    while True:

        try:

            entrada = input(
                "\nEscolha as portas MIDI: "
            ).strip()

            indices = [
                int(x.strip())
                for x in entrada.split(",")
            ]

            for idx in indices:
                if idx < 0 or idx >= len(portas):
                    raise ValueError

            break

        except ValueError:
            print("Seleção inválida.")

    portas_selecionadas = [
        portas[idx]
        for idx in indices
    ]

    midi_config = {
        "midi": {
            "inputs": [
                {
                    "name": porta
                }
                for porta in portas_selecionadas
            ]
        }
    }

    print("\n" + "=" * 60)
    print("CONFIGURAÇÃO MIDI")
    print("=" * 60)

    print(
        json.dumps(
            midi_config,
            indent=4,
            ensure_ascii=False
        )
    )

    return midi_config

def gravar_midi(midi_config, output_file=None):
    """
    Grava eventos MIDI e salva em um arquivo .mid

    Args:
        midi_config (dict): Configuração gerada por configurar_midi()
        output_file (str | None): Nome do arquivo de saída

    Returns:
        str: caminho do arquivo gerado
    """

    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"gravacao_midi_{timestamp}.mid"

    # Abrir portas MIDI
    portas = []

    for porta_cfg in midi_config["midi"]["inputs"]:
        portas.append(
            mido.open_input(
                porta_cfg["name"]
            )
        )

    print("\nPressione ENTER para iniciar a gravação...")
    input()

    print("Gravando MIDI...")
    print("Pressione ENTER novamente para finalizar.")

    stop_event = threading.Event()

    def aguardar_parada():
        input()
        stop_event.set()

    threading.Thread(
        target=aguardar_parada,
        daemon=True
    ).start()

    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)

    ultimo_evento = time.perf_counter()

    try:

        while not stop_event.is_set():

            houve_evento = False

            for porta in portas:

                for msg in porta.iter_pending():

                    agora = time.perf_counter()

                    delta = agora - ultimo_evento
                    ultimo_evento = agora

                    ticks = int(
                        mido.second2tick(
                            delta,
                            mid.ticks_per_beat,
                            500000
                        )
                    )

                    msg_copy = msg.copy(
                        time=ticks
                    )

                    track.append(msg_copy)

                    houve_evento = True

            if not houve_evento:
                time.sleep(0.001)

    finally:

        for porta in portas:
            porta.close()

        mid.save(output_file)

        print(f"\nArquivo MIDI salvo: {output_file}")

    return output_file