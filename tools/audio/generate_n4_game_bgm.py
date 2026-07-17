#!/usr/bin/env python3
"""Generate the N4 Kyushu/Shikoku game background music loop.

This is the lighter onsen-street walk arrangement for gameplay. It keeps the
track to shinobue, smooth harmony, and soft bass. The existing
``generate_n4_bgm.py`` script remains the quiet vocabulary-review focus BGM.

給剛開始看音訊程式的人：

這支檔案不是讀取現成樂器音源，而是用 Python 直接「算出聲波」。
可以把它想成：我們準備兩條很長的陣列 left/right，代表左右聲道。
每個樂器函式都會在指定時間，把自己的波形加到這兩條陣列裡。
最後 write_wav() 再把陣列轉成真正的 .wav 檔。

整體流程：
1. 設定歌曲速度、長度、輸出路徑。
2. 建立左右聲道的空白音訊陣列。
3. 用 arrange() 安排和弦與旋律。
4. 用 write_wav() 做簡單壓限與輸出。

目前這版刻意保持簡單，只保留：
- shinobue / 篠笛：主旋律
- smooth harmony / 平滑和聲：支撐篠笛，不使用撥弦顆粒聲
- soft bass / 淡低音：讓音樂不會太薄

注意：這是 N4「遊戲」BGM。N4「複習」BGM 是 generate_n4_bgm.py，
不要在這支檔案裡改複習音樂的設定。
"""

from __future__ import annotations

from array import array
import math
import struct
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 音訊採樣率。44_100 代表每秒 44100 個 sample，是常見 CD 音質。
# 數字越高檔案越大、計算越慢；這裡 44100 已經夠用。
SAMPLE_RATE = 44_100

# BPM 是歌曲速度，124 BPM 代表一分鐘 124 拍。
# 這首是輕快散步感，所以比抒情曲快，但沒有到戰鬥音樂那麼急。
BPM = 124

# 每一拍幾秒。後面所有 bar/beat 都會靠這個換算成實際秒數。
BEAT_SECONDS = 60 / BPM

# 一小節 4 拍，這就是常見的 4/4 拍。
BEATS_PER_BAR = 4

# 總共 48 小節。搭配 124 BPM，最後長度大約 92.9 秒。
BARS = 48
DURATION_SECONDS = BARS * BEATS_PER_BAR * BEAT_SECONDS

# 這支腳本只輸出 WAV。MP3/OGG 是用 ffmpeg 從 WAV 轉出來的。
OUTPUT_PATH = PROJECT_ROOT / "web" / "assets" / "audio" / "n4-kyushu-shikoku-game-bgm.wav"

def midi_to_hz(midi_note: float) -> float:
    """把 MIDI 音高編號轉成 Hz 頻率。

    音訊合成最後都要回到「頻率」。
    例如 A4 的 MIDI 編號是 69，頻率是 440 Hz。
    MIDI 數字每增加 12，就升高一個八度，頻率會變成 2 倍。
    """
    return 440.0 * (2 ** ((midi_note - 69) / 12))


# 這裡把人類比較看得懂的音名，對應到 MIDI 音高。
# 例如 "G4": 67，代表第四組八度的 G。
# 如果旋律想加新音，通常要先在這裡補音名。
NOTE_MIDI = {
    "G2": 43,
    "D3": 50,
    "E3": 52,
    "G3": 55,
    "A3": 57,
    "B3": 59,
    "C4": 60,
    "D4": 62,
    "E4": 64,
    "F#4": 66,
    "G4": 67,
    "A4": 69,
    "B4": 71,
    "C5": 72,
    "D5": 74,
    "E5": 76,
    "G5": 79,
    "A5": 81,
    "B5": 83,
}


def note(name: str) -> float:
    """用音名取得頻率。

    例如 note("G4") 會先查 NOTE_MIDI，再轉成 Hz。
    後面的旋律資料就能寫 "G4"、"D5"，不用自己算頻率。
    """
    return midi_to_hz(NOTE_MIDI[name])


def beat_time(bar: int, beat: float = 0.0) -> float:
    """把「第幾小節、第幾拍」換成秒數。

    bar 從 0 開始算：
    - bar=0, beat=0.0 是歌曲一開始
    - bar=4, beat=0.0 是第 5 小節開頭
    - bar=4, beat=1.5 是第 5 小節第 1.5 拍

    這樣安排音樂比直接寫秒數好懂很多。
    """
    return (bar * BEATS_PER_BAR + beat) * BEAT_SECONDS


# 先建立左右聲道的空白音訊陣列。
# array("f") 是浮點數陣列；每個位置代表某一瞬間的音量。
# 之後所有樂器都會把自己的聲音加到 left/right 裡。
sample_count = int(DURATION_SECONDS * SAMPLE_RATE)
left = array("f", [0.0]) * sample_count
right = array("f", [0.0]) * sample_count


def equal_power_pan(value: float) -> tuple[float, float]:
    """把 pan 值轉成左右聲道音量。

    pan 的範圍：
    - -1.0：完全靠左
    -  0.0：中間
    -  1.0：完全靠右

    這裡用 equal-power panning，聽起來會比單純 left/right 線性縮放自然。
    """
    pan = max(-1.0, min(1.0, value))
    angle = (pan + 1.0) * math.pi / 4
    return math.cos(angle), math.sin(angle)


def add_sample(index: int, value: float, pan: float) -> None:
    """把某一個 sample 音量加進左右聲道。

    index 是音訊陣列的位置，value 是這一瞬間要加的音量。
    注意這裡是「加上去」，不是覆蓋，所以很多樂器可以同時發聲。
    """
    if 0 <= index < sample_count:
        left_gain, right_gain = equal_power_pan(pan)
        left[index] += value * left_gain
        right[index] += value * right_gain


def envelope(position: float, duration: float, attack: float, release: float, curve: float = 0.8) -> float:
    """計算一個音在當下應該多大聲。

    envelope 就是音量包絡，控制聲音怎麼開始、怎麼結束。

    重要參數：
    - attack：起音時間。越短越硬、越容易有爆音感；越長越柔。
    - release：收尾時間。越長尾巴越自然，但也可能糊。
    - curve：中段衰減速度。數字越大，聲音越快變小。
    """
    if position < 0 or position >= duration:
        return 0.0
    if position < attack:
        return position / max(attack, 0.0001)
    if position > duration - release:
        return max(0.0, (duration - position) / max(release, 0.0001))
    body = (position - attack) / max(duration - attack - release, 0.0001)
    return math.exp(-body * curve)


def add_tone(
    start: float,
    duration: float,
    frequency: float,
    amplitude: float,
    *,
    pan: float = 0.0,
    attack: float = 0.02,
    release: float = 0.18,
    waveform: str = "sine",
    vibrato_depth: float = 0.0,
    vibrato_rate: float = 4.8,
    curve: float = 0.65,
    breath: float = 0.0,
) -> None:
    """加入一段持續音，適合做篠笛、低音、暖和弦。

    這個函式會逐 sample 產生基本波形，再套上 envelope。

    重要參數：
    - start：聲音開始秒數
    - duration：聲音持續秒數
    - frequency：頻率，單位 Hz
    - amplitude：音量，數字越大越大聲
    - pan：左右位置
    - waveform："flute"、"warm"、"triangle" 或預設 sine
    - vibrato_depth/rate：顫音深度與速度，主要給篠笛一點活感
    - breath：氣聲量。現在預設不用，避免背景出現顆粒感。
    """
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    phase = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        current_frequency = frequency * (1 + vibrato_depth * math.sin(math.tau * vibrato_rate * t))
        phase += math.tau * current_frequency / SAMPLE_RATE

        # 這裡不是精準模擬真實樂器，只是用幾個泛音做「像那個方向」的音色。
        # flute：比較適合主旋律；warm：比較適合低音或柔和支撐。
        if waveform == "flute":
            tone = (
                math.sin(phase)
                + 0.13 * math.sin(phase * 2.01)
                + 0.05 * math.sin(phase * 3.0)
            )
        elif waveform == "warm":
            tone = math.sin(phase) + 0.20 * math.sin(phase * 2.0) + 0.06 * math.sin(phase * 3.0)
        elif waveform == "triangle":
            tone = 2 * abs(2 * ((phase / math.tau) % 1) - 1) - 1
        else:
            tone = math.sin(phase)
        air = 0.0
        env = envelope(t, duration, attack, release, curve)
        add_sample(start_index + offset, (tone + air) * amplitude * env, pan)


def add_bass(start: float, duration: float, frequency: float, amplitude: float) -> None:
    """加入淡低音。

    前面曾經有「低音聽起來像爆音」的問題，所以這裡刻意：
    - attack 設為 0.060，讓低音不要瞬間衝出來
    - release 設為 0.24，讓收尾比較平
    - amplitude 在 add_chord_bar() 裡控制，前 4 小節會更小聲
    """
    add_tone(
        start,
        duration,
        frequency,
        amplitude,
        pan=-0.05,
        attack=0.060,
        release=0.24,
        waveform="warm",
        curve=0.62,
    )


def add_flute_phrase(bar: int, phrase: list[tuple[float, str, float]], *, amp: float = 0.076) -> None:
    """加入一串篠笛旋律。

    phrase 的格式是：
        (beat, note_name, length)

    例如：
        (1.5, "D5", 0.72)

    代表從該小節第 1.5 拍開始，吹 D5，長度 0.72 拍。
    這種寫法比較像在寫樂譜，不用每個音都自己換算秒數。
    """
    for beat, name, length in phrase:
        add_tone(
            beat_time(bar, beat),
            length * BEAT_SECONDS,
            note(name),
            amp,
            pan=0.07,
            attack=0.035,
            release=0.12,
            waveform="flute",
            vibrato_depth=0.003,
            vibrato_rate=5.2,
            curve=0.30,
            breath=0.0,
        )


def add_chord_bar(bar: int, names: tuple[str, str, str], bass_name: str) -> None:
    """加入某一小節的平滑和聲與淡低音。

    names 是三個和聲音，bass_name 是低音音名。

    這裡有兩個刻意設計：
    1. 和聲用 add_tone() 的 warm 波形，不使用短促撥弦合成。
       這樣可以避開短促撥弦帶來的背景顆粒感。
    2. 前 4 小節 bass_amp 比較小，避免歌曲一開始低音太重。
       這是針對前段低音爆感做的處理。
    """
    start = beat_time(bar)
    for index, name in enumerate(names):
        add_tone(
            start,
            1.80 * BEAT_SECONDS,
            note(name),
            0.010,
            pan=-0.18 + index * 0.18,
            attack=0.14,
            release=0.36,
            waveform="warm",
            curve=0.18,
        )
    bass_amp = 0.012 if bar < 4 else 0.030
    add_bass(start + 0.035, 1.05 * BEAT_SECONDS, note(bass_name), bass_amp)


def arrange() -> None:
    """安排整首曲子的所有樂器。

    這是整支腳本最像「編曲」的地方。
    上面的函式是在定義樂器，這裡是在決定：
    - 哪個小節放哪個和弦
    - 篠笛什麼時候吹什麼旋律

    目前沒有太鼓、鈴、木琴、拍子木、三味線、箏撥弦，
    也沒有持續環境底噪。
    如果以後要加樂器，建議先在這裡少量試，不要一次塞太多。
    """
    # 8 小節一輪的和弦進行。
    # 每個項目格式是：
    #   ((和聲音1, 和聲音2, 和聲音3), 低音)
    #
    # 這組和弦會重複 6 次，剛好 48 小節。
    chord_cycle = [
        (("G3", "B3", "D4"), "G2"),
        (("D3", "A3", "D4"), "D3"),
        (("E3", "G3", "B3"), "E3"),
        (("B3", "D4", "F#4"), "B3"),
        (("C4", "E4", "G4"), "C4"),
        (("G3", "B3", "D4"), "G2"),
        (("A3", "C4", "E4"), "A3"),
        (("D3", "A3", "D4"), "D3"),
    ]
    for bar in range(BARS):
        names, bass_name = chord_cycle[bar % len(chord_cycle)]
        add_chord_bar(bar, names, bass_name)

    # intro：前奏，讓玩家進入 N4 地區時有一個簡短開場。
    intro = [(0.0, "B4", 0.42), (0.5, "D5", 0.48), (1.0, "G5", 0.84), (2.5, "A5", 0.42), (3.0, "G5", 0.70)]

    # A 段主旋律：最主要、最容易記的旋律。
    a_phrase = [
        (0.0, "G4", 0.40),
        (0.5, "A4", 0.40),
        (1.0, "B4", 0.42),
        (1.5, "D5", 0.72),
        (2.5, "B4", 0.36),
        (3.0, "A4", 0.36),
        (3.5, "G4", 0.48),
        (4.0, "E4", 0.38),
        (4.5, "G4", 0.38),
        (5.0, "A4", 0.40),
        (5.5, "B4", 0.66),
        (6.5, "A4", 0.38),
        (7.0, "G4", 0.38),
        (7.5, "E4", 0.50),
    ]

    # A' 段變奏：跟 A 段類似，但尾巴稍微不一樣，避免一直重複太死。
    a_turn = [
        (0.0, "G4", 0.38),
        (0.5, "A4", 0.38),
        (1.0, "B4", 0.38),
        (1.5, "D5", 0.48),
        (2.0, "E5", 0.40),
        (2.5, "D5", 0.38),
        (3.0, "B4", 0.36),
        (3.5, "A4", 0.44),
        (4.0, "G4", 0.36),
        (4.5, "A4", 0.36),
        (5.0, "B4", 0.38),
        (5.5, "G4", 0.46),
        (6.5, "A4", 0.46),
        (7.25, "G4", 0.62),
    ]

    # B 段：稍微開闊一點，像走到溫泉街街尾看到河邊或燈籠。
    b_phrase = [
        (0.0, "C5", 0.62),
        (1.0, "D5", 0.62),
        (2.0, "G5", 0.84),
        (3.0, "E5", 0.56),
        (4.0, "C5", 0.54),
        (5.0, "D5", 0.56),
        (6.0, "B4", 0.42),
        (6.5, "D5", 0.42),
        (7.0, "E5", 0.72),
    ]

    # loop_tag：結尾過門。最後會回到開頭，所以這段不能太突兀。
    loop_tag = [
        (0.0, "B4", 0.36),
        (0.5, "D5", 0.36),
        (1.0, "G5", 0.58),
        (2.0, "A5", 0.36),
        (2.5, "G5", 0.36),
        (3.0, "E5", 0.48),
        (4.0, "D5", 0.42),
        (4.5, "B4", 0.42),
        (5.0, "A4", 0.46),
        (6.0, "G4", 0.84),
    ]

    # 篠笛段落安排。
    # 數字 0/4/12... 是從第幾小節開始吹。
    add_flute_phrase(0, intro, amp=0.066)
    add_flute_phrase(4, a_phrase)
    add_flute_phrase(12, a_turn)
    add_flute_phrase(20, a_phrase)
    add_flute_phrase(28, b_phrase, amp=0.072)
    add_flute_phrase(36, a_turn)
    add_flute_phrase(44, loop_tag, amp=0.070)


def soft_limit(value: float) -> float:
    """簡單的 soft limiter，避免音量超出 -1.0 到 1.0 太多。

    直接硬切音量會產生很難聽的破音。
    tanh 會把太大的音量比較柔地壓回來。
    這不是專業 mastering，只是讓輸出比較安全。
    """
    return math.tanh(value * 0.92) / math.tanh(0.92)


def write_wav() -> None:
    """把 left/right 陣列寫成 WAV 檔。

    WAV 檔需要整數 sample，這裡會：
    1. 找出整首歌最大峰值 peak。
    2. 算 normalize，讓最大音量留一點空間，不要頂到 0 dB。
    3. 用 soft_limit() 再壓一下峰值。
    4. 寫成 16-bit stereo PCM WAV。

    如果輸出太小聲，可以調 normalize = 0.60 / peak 的 0.60。
    但不要一次拉太高，不然容易爆音。音訊很現實，太貪心就會報復你。
    """
    peak = max(max(abs(value) for value in left), max(abs(value) for value in right), 0.0001)
    normalize = 0.60 / peak

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUTPUT_PATH), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        for l_value, r_value in zip(left, right):
            l_int = int(max(-1, min(1, soft_limit(l_value * normalize))) * 32767)
            r_int = int(max(-1, min(1, soft_limit(r_value * normalize))) * 32767)
            output.writeframes(struct.pack("<hh", l_int, r_int))


def main() -> None:
    """主程式入口。

    執行：
        python3 tools/audio/generate_n4_game_bgm.py

    會重新產生：
        web/assets/audio/n4-kyushu-shikoku-game-bgm.wav

    注意：MP3 和 OGG 不會在這裡自動產生，需要另外用 ffmpeg 從 WAV 轉檔。
    """
    arrange()
    write_wav()
    print(f"Wrote {OUTPUT_PATH} ({DURATION_SECONDS:.2f}s, {BPM} BPM)")


if __name__ == "__main__":
    main()
