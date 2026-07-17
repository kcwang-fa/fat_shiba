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

    ── 為什麼改成這版（消除喀喀聲的關鍵）──
    舊版把 attack / body / release 三段用不同數學式硬接：
    attack 是線性、body 是 exp 指數、release 又是線性。
    這三段在「接縫」的數值對不起來，會一階不連續（斜率突變）。
    乘上波形後就在音符中段與收尾各留一個小階梯 = click（喀喀）。
    單一個音時階梯很小；但和聲三音、篠笛多音同時發聲，
    多個階梯在相近時間點累加，就爆成聽得見的喀喀聲。
    這也解釋了：和聲出現→兩個喀喀；篠笛（更多短音）→更多喀喀。

    這版讓三段接縫「數值連續」：
    - attack 用餘弦 0→1，末端剛好等於 1，與 body 起點 exp(0)=1 銜接。
    - release 從 body 段末端的實際值開始，用餘弦平滑淡到 0，不再獨立線性。
    """
    if position < 0 or position >= duration:
        return 0.0
    # 夾制：attack + release 不能超過整個音長，否則兩段會重疊、邏輯錯亂。
    # 短音（如馬林巴）常遇到 release 比音還長的情況，這裡按比例縮回，
    # 確保 body 段至少留一點，三段接縫都連續、不產生 click。
    att = max(attack, 0.0001)
    rel = max(release, 0.0001)
    if att + rel > duration * 0.98:
        scale = duration * 0.98 / (att + rel)
        att *= scale
        rel *= scale
    body_len = max(duration - att - rel, 0.0001)
    if position < att:
        # 餘弦起音：0 → 1，末端斜率為 0，且末端值 = 1 與 body 起點連續
        return 0.5 - 0.5 * math.cos(math.pi * (position / att))
    if position <= duration - rel:
        # body：指數衰減，從 1（exp(0)）開始
        body = (position - att) / body_len
        return math.exp(-body * curve)
    # release：起始值 = body 段真實末端值（body_len 對應 body=1），餘弦淡到 0。
    # 動態計算而非寫死 exp(-curve)，確保任何音長下接縫都連續。
    v_end = math.exp(-1.0 * curve)
    x = (duration - position) / rel  # 1 → 0
    return v_end * (0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, x))))



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
    breath_lp = 0.0  # 氣聲一階低通濾波器的狀態，跨 sample 累積出柔和風聲

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
        elif waveform == "marimba":
            # 木琴/馬林巴：基音為主，加一個高泛音（約 4 倍）帶出木頭「叩」的圓潤感。
            # 泛音刻意用 3.9 而非整數 4.0，模擬真實木條略帶非諧波的敲擊色彩，
            # 聽起來更像木質而非電子純音，但幅度很小以免顆粒化。
            tone = (
                math.sin(phase)
                + 0.22 * math.sin(phase * 3.9)
                + 0.05 * math.sin(phase * 9.2)
            )
        elif waveform == "koto":
            # 箏（こと）：日本弦樂器。特徵是清亮的基音加上一串諧波泛音，
            # 帶一點金屬弦的光澤，但整體綿延、能歌唱，不像馬林巴敲一下就收。
            # 用基音 + 2/3/4/5 倍音，幅度遞減，做出「弦」的豐富但不刺耳的音色。
            # 跟篠笛同屬和風世界，質感是「線」而非「點」，兩者對唱才協調。
            tone = (
                math.sin(phase)
                + 0.35 * math.sin(phase * 2.0)
                + 0.18 * math.sin(phase * 3.0)
                + 0.10 * math.sin(phase * 4.0)
                + 0.05 * math.sin(phase * 5.0)
            )
        elif waveform == "shakuhachi":
            # 尺八：跟篠笛同為竹笛家族，但真實尺八的靈魂在於它「不乾淨」——
            # 音高會微微晃、泛音不規則、整段都有氣息摩擦。純諧波正弦太完美，
            # 聽起來就是合成器，所以這裡刻意加入不規則性：
            #   1. drift：極緩慢的音高漂移（約 0.7Hz），模擬吹奏時氣壓的自然起伏，
            #      破除數位死板的「定音」感。
            #   2. 泛音用 2.003 / 3.005 這種略偏整數的比例，加一點非諧波色彩，
            #      像真實竹管那樣泛音不會數學完美對齊。
            #   3. 泛音幅度隨時間微微起伏，音色會呼吸而非一成不變。
            drift = 0.004 * math.sin(math.tau * 0.7 * t + 0.5)
            p = phase * (1.0 + drift)
            shimmer = 1.0 + 0.12 * math.sin(math.tau * 3.3 * t)
            tone = (
                math.sin(p)
                + 0.14 * shimmer * math.sin(p * 2.003)
                + 0.05 * math.sin(p * 3.005 + 0.3)
            )
        elif waveform == "triangle":
            tone = 2 * abs(2 * ((phase / math.tau) % 1) - 1) - 1
        else:
            tone = math.sin(phase)
        # 氣聲：尺八的靈魂。真實氣息是「寬頻、隨機、跟音高無關」的空氣摩擦，
        # 之前用兩個正弦相乘其實是固定諧波、還是電子感，這裡改成真正的
        # 確定性偽隨機噪音（用整數 hash，不靠 random 模組，保持可重現）。
        # 關鍵控制：
        # 1. 用一階低通把白噪音濾成柔和的「風聲」，不是尖銳的沙沙。
        # 2. 氣息延續整個音（不只音頭），但音頭稍強，像持續吹氣。
        # 3. 下面 (tone+air)*env 會把氣聲一起乘上包絡，音收了氣聲也收，
        #    不會殘留成背景底噪——這是它不會變回沙沙問題的關鍵。
        if breath > 0.0:
            n = (start_index + offset) * 1103515245 + 12345
            n = (n ^ (n >> 16)) & 0x7FFFFFFF
            white = (n / 0x3FFFFFFF) - 1.0  # -1..1 的偽隨機白噪音
            breath_lp = breath_lp * 0.86 + white * 0.14  # 一階低通 → 柔和風聲
            head = 0.6 + 0.4 * math.exp(-t * 4.0)  # 音頭稍強，之後維持氣息底
            air = breath * head * breath_lp
        else:
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


def add_shakuhachi_phrase(bar: int, phrase: list[tuple[float, str, float]], *, amp: float = 0.076) -> None:
    """加入一串「低八度篠笛」答句。

    音色跟篠笛主旋律完全相同（同樣的 flute 波形與所有參數），
    差別只在音高降了一個八度、以及 pan 偏左做左右區隔。
    這樣答句聽起來就是同一支篠笛的低八度回應，融合度最高、質感 100% 一致。

    參數刻意跟 add_flute_phrase 對齊：
    - waveform="flute"、attack 0.035、release 0.12、
      vibrato 0.003/5.2、curve 0.30、breath 0.0（篠笛不用氣聲，避免雜訊）。
    - amp 預設 0.076，跟篠笛同音量。
    - pan=-0.12 偏左，跟偏右（+0.07）的篠笛主旋律分開，形成左右對唱。
    - envelope 已有自動夾制，release 不會長於音長，不產生 click。
    """
    for beat, name, length in phrase:
        add_tone(
            beat_time(bar, beat),
            length * BEAT_SECONDS,
            note(name),
            amp,
            pan=-0.12,
            attack=0.035,
            release=0.12,
            waveform="flute",
            vibrato_depth=0.003,
            vibrato_rate=5.2,
            curve=0.30,
            breath=0.0,
        )


def add_chord_bar(bar: int, names: tuple[str, str, str], bass_name: str, avoid: set[str] | None = None) -> None:
    """加入某一小節的平滑和聲與淡低音。

    names 是三個和聲音，bass_name 是低音音名。
    avoid 是「這小節要讓路的音名集合」：若某個和聲音落在 avoid 裡，
    就大幅減弱它，把那個頻率讓給尺八答句，避免兩個相同音高的音疊在
    一起產生相位干涉的「雙音」。這是在尺八低八度答句的小節才會用到。

    這裡有兩個刻意設計：
    1. 和聲用 add_tone() 的 warm 波形，不使用短促撥弦合成。
       這樣可以避開短促撥弦帶來的背景顆粒感。
    2. 前 4 小節 bass_amp 比較小，避免歌曲一開始低音太重。
       這是針對前段低音爆感做的處理。
    """
    avoid = avoid or set()
    start = beat_time(bar)
    for index, name in enumerate(names):
        # 撞到尺八答句的音就讓路：音量大幅降低（不完全拿掉，留一點厚度）。
        amp = 0.010
        if name in avoid:
            amp = 0.002
        add_tone(
            start,
            1.80 * BEAT_SECONDS,
            note(name),
            amp,
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
    # 先算出「每個小節要讓路的和聲音」對照表。
    # 尺八答句在低八度，會跟和聲撞頻，所以答句小節的和聲要避開答句用到的音。
    # 這裡定義答句用的音（跟後面 shakuhachi_answer 一致），並標出它在哪些小節。
    answer_notes_by_chord = {
        "G":  {"B3", "D4"},
        "D":  {"A3", "D4"},
        "Em": {"B3", "E4"},
        "Bm": {"D4", "B3"},
        "C":  {"C4", "E4"},
        "Am": {"A3", "C4"},
    }
    chord_name_by_bar = ["G", "D", "Em", "Bm", "C", "G", "Am", "D"]
    # 尺八答句所在的小節（篠笛空檔）：
    answer_bars = {
        1, 2, 3, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19,
        22, 23, 24, 25, 26, 27, 30, 31, 32, 33, 34, 35,
        38, 39, 40, 41, 42, 43, 46, 47,
    }
    avoid_by_bar = {}
    for bar in answer_bars:
        chord = chord_name_by_bar[bar % 8]
        avoid_by_bar[bar] = answer_notes_by_chord[chord]

    for bar in range(BARS):
        names, bass_name = chord_cycle[bar % len(chord_cycle)]
        add_chord_bar(bar, names, bass_name, avoid=avoid_by_bar.get(bar))

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

    # 尺八答句安排 —— 問答式（call-and-response），貫穿全曲。
    #
    # 篠笛其實只吹每段的前 2 小節，後面留下大片空檔。實測篠笛完全靜音的
    # 連續區塊有七塊：
    #   bar1–3、bar6–11、bar14–19、bar22–27、bar30–35、bar38–43、bar46–47
    # 尺八就鋪進這些空檔，成為篠笛樂句之間的「答句」，
    # 篠笛講兩小節 → 尺八以低八度答幾小節，像同一支竹笛的高低兩種表情，
    # 整首都有一來一往的呼吸感。
    # （和聲與低音仍持續，所以空檔不會真的沒聲，只是主旋律讓給尺八。）
    #
    # 每個答句的音都跟著當下和弦走（和弦進行 8 小節一輪：
    # G / D / Em / Bm / C / G / Am / D），落在和弦內音，確保和諧。

    def shakuhachi_answer(chord):
        """依和弦名回傳一小節的「低八度篠笛」答句。

        音高落在篠笛主旋律的低八度（G3–E4 一帶），音色跟篠笛完全相同，
        聽起來就是同一支篠笛的低八度回應。

        撞頻處理（重要）：這個低八度正是和聲層 warm 音的地盤，直接放會
        跟和聲撞在同一頻率、產生「雙音」。所以在 arrange() 裡，這些答句
        小節的和聲會「讓路」——暫時避開跟尺八答句相同的音，把低八度空間
        讓給答句。這樣既保住低八度的完整效果，又不撞頻。

        其餘：音短（0.6～0.7 拍）頓點明顯；起拍延後一拍（第 1、第 2.5 拍）
        跟篠笛錯開成一拍問答。長度單位為「拍」，音之間的空隙就是換氣。
        """
        table = {
            "G":  [(1.0,"B3",0.6),(2.5,"D4",0.7)],
            "D":  [(1.0,"A3",0.6),(2.5,"D4",0.7)],
            "Em": [(1.0,"B3",0.6),(2.5,"E4",0.7)],
            "Bm": [(1.0,"D4",0.6),(2.5,"B3",0.7)],
            "C":  [(1.0,"C4",0.6),(2.5,"E4",0.7)],
            "Am": [(1.0,"A3",0.6),(2.5,"C4",0.7)],
        }
        return table[chord]

    # 和弦進行對照（跟 chord_cycle 一致，8 小節一輪）：
    #   bar%8: 0=G 1=D 2=Em 3=Bm 4=C 5=G 6=Am 7=D
    chord_by_bar = ["G","D","Em","Bm","C","G","Am","D"]

    # 篠笛空檔小節，逐一放上對應和弦的尺八答句。
    # 答句本身已整體延後一拍（首音起於第 1 拍），離前一段篠笛的 release
    # 尾韻夠遠，不需再對第一小節做特殊延後，每小節一律照拍點起。
    flute_gap_blocks = [
        [1, 2, 3],
        [6, 7, 8, 9, 10, 11],
        [14, 15, 16, 17, 18, 19],
        [22, 23, 24, 25, 26, 27],
        [30, 31, 32, 33, 34, 35],
        [38, 39, 40, 41, 42, 43],
        [46, 47],
    ]
    for block in flute_gap_blocks:
        for gap_bar in block:
            chord = chord_by_bar[gap_bar % 8]
            add_shakuhachi_phrase(gap_bar, shakuhachi_answer(chord))


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
    4. 加 TPDF dither 後用 round 寫成 16-bit stereo PCM WAV。

    ── 這版對「沙沙聲」的處理 ──
    這首合成出來很小聲（peak 約 0.087），normalize 要放大約 6.9 倍。
    微小訊號量化成 16-bit 時只用到極少量化階，會在相鄰整數階之間
    反覆橫跳，產生全程均勻的量化階梯噪音，聽起來就是沙沙聲。
    兩個對策：
    (a) round 取代 int 截斷，量化誤差不再固定偏一個方向。
    (b) TPDF dither：加入兩個獨立均勻亂數相減的微量抖動，
        把規律的量化失真去相關成聽感無害的均勻底噪。
    真正的根治是「在合成時就把各樂器 amplitude 整體調大」，
    讓 peak 自然接近滿刻度、放大倍率趨近 1——那要動編曲，這裡先用 dither。
    """
    import random

    peak = max(max(abs(value) for value in left), max(abs(value) for value in right), 0.0001)
    normalize = 0.60 / peak

    def to_int16(value: float) -> int:
        v = max(-1.0, min(1.0, soft_limit(value * normalize)))
        v += (random.random() - random.random()) / 32768.0  # TPDF dither
        return max(-32768, min(32767, int(round(v * 32767))))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUTPUT_PATH), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for l_value, r_value in zip(left, right):
            frames += struct.pack("<hh", to_int16(l_value), to_int16(r_value))
        output.writeframes(bytes(frames))


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
