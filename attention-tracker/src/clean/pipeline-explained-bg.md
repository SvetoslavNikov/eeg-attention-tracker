# `src/clean/pipeline.py` — обяснение от начало до край

Този файл е companion explanation към `pipeline.py`. Представи си, че седим до файла и го четем ред по ред. Целта на кода е:

1. Да вземе един `EEGSession`, тоест обект, който държи EEG запис.
2. Да копира неговата `data` матрица.
3. Да приложи `band-pass` filter върху всеки EEG channel.
4. Да намери много големи отклонения, наречени тук artifacts или spikes.
5. Да поправи кратките artifacts чрез linear interpolation.
6. Да върне нов `EEGSession` със същите metadata, но с почистена `data`.

Важно: файлът не зарежда EEG данни от диск, не рисува графики и не пресмята attention score. Той е една стъпка от pipeline-а:

```text
LYS .npz -> EEGSession -> clean -> features -> score -> plot
```

Тук сме само в частта `clean`.

---

## Начало на файла

```python
"""Signal cleaning for LYS EEGSession."""
```

Това е module docstring. В Python string literal, който стои най-отгоре във файла, служи като описание на целия module.

Буквално тук не се създава променлива, която кодът после използва. Python записва този текст като `__doc__` на module-а. Ако някой инструмент или човек поиска документация за този module, може да види този текст.

Смисълът е: този файл се занимава със signal cleaning за `LYS EEGSession`.

`LYS` е част от domain context-а на проекта. От този файл не можем напълно да разберем какво значи LYS, но от останалия проект се вижда, че има LYS EEG data и тя се представя като `EEGSession`.

---

```python
from __future__ import annotations
```

Това е специален Python import. `__future__` позволява поведение от по-нови версии на Python да се активира по контролиран начин.

Конкретно `annotations` влияе на type hints. Type hints са неща като:

```python
session: EEGSession
interp_max_samples: int | None
) -> EEGSession
```

Те казват на човека и на tools какъв type се очаква, но обикновено не променят runtime логиката.

С този import annotations могат да се обработват по-отложено. За нас най-практичното значение е: файлът може спокойно да използва modern type hint syntax като `int | None`.

Input няма. Операцията е import-time configuration. Резултатът е промяна в начина, по който Python третира annotations в този module.

До този момент имаме само описание на module-а и настройка за type hints. Няма EEG data, няма filtering, няма функции извикани от нас.

---

## Imports

```python
import numpy as np
```

Това import-ва library `numpy` и му дава кратко име `np`.

`numpy` е основна Python library за работа с arrays и числени изчисления. В този файл EEG data се обработва като `np.ndarray`.

`np.ndarray` можеш да си го представиш като таблица от числа. В този проект `session.data` е двумерен array:

```text
rows    -> samples във времето
columns -> EEG channels
shape   -> (n_samples, 4)
```

Пример:

```text
data =
[
  [ 1.2,  0.8, -0.5,  2.0],   sample 0, channels 0..3
  [ 1.1,  0.7, -0.4,  2.2],   sample 1
  [ 1.3,  0.9, -0.6,  2.1],   sample 2
]
```

След този ред името `np` сочи към `numpy` module-а. По-надолу, когато видим `np.array`, `np.median`, `np.abs`, `np.any`, `np.zeros`, `np.arange`, `np.interp`, всички те идват от `numpy`.

---

```python
from scipy.signal import butter, filtfilt
```

Това import-ва две функции от `scipy.signal`.

`scipy` е scientific computing library. Подmodule-ът `scipy.signal` съдържа инструменти за signal processing.

Тук import-ваме:

- `butter`: функция, която design-ва Butterworth filter и връща filter coefficients.
- `filtfilt`: функция, която прилага filter върху signal forward и backward, за да получи zero-phase filtering.

Implementation-ът на тези функции не е в този файл. Затова можем да кажем как се използват според API-то им, но не можем от този файл да видим вътрешните им numerical algorithms ред по ред.

Практически:

```python
b, a = butter(...)
```

създава coefficients.

```python
filtered = filtfilt(b, a, signal, padlen=...)
```

прилага filter-а върху 1-D signal и връща нов 1-D `np.ndarray` със filtered values.

---

```python
from common.session import EEGSession
```

Това import-ва class `EEGSession` от module `common.session`.

Class е шаблон за обекти. Instance е конкретен обект, създаден от class-а.

В този проект `EEGSession` представлява един EEG recording. От `src/common/session.py` се вижда, че `EEGSession` има attributes като:

- `data`: `np.ndarray` с shape `(n_samples, 4)`
- `fs`: sampling rate, например `500.0`
- `ch_names`: имената на 4 channels
- `time`: time axis, shape `(n_samples,)`
- `subject_id`, `study_id`, `phases`, `source_path`

С други думи, `EEGSession` е container за EEG signal плюс metadata.

Този файл приема `EEGSession` като input и връща `EEGSession` като output.

До този момент файлът е подготвил tools:

```text
numpy -> arrays и math
scipy.signal -> filter design и filtering
EEGSession -> project-specific object за EEG recording
```

---

## Функцията `clean`

```python
def clean(
    session: EEGSession,
    *,
    fmin: float = 0.5,
    fmax: float = 40.0,
    artifact_z: float = 8.0, #?
    interp_max_samples: int | None = None, #?
) -> EEGSession:
```

Тук се дефинира функция с име `clean`.

Когато Python стигне до `def`, той не изпълнява тялото на функцията веднага. Той създава function object и го записва под името `clean`. Реалното почистване започва чак когато някой извика:

```python
clean(session)
```

или:

```python
clean(session, fmin=1.0, fmax=35.0)
```

Нека разбием signature-а.

```python
session: EEGSession
```

`session` е първият argument. Очаква се да е instance на `EEGSession`.

Type hint-ът `: EEGSession` не е runtime проверка сам по себе си. Той казва: "Тази функция е написана с очакването `session` да е `EEGSession`." Ако подадеш нещо друго, Python няма автоматично да спре само заради hint-а, но кодът вероятно ще гръмне, когато опита `session.data` или `session.fs`.

```python
*
```

Самостоятелната `*` в function signature означава: всички parameters след нея са keyword-only.

Тоест това е валидно:

```python
clean(session, fmin=1.0)
```

А това не е валидно:

```python
clean(session, 1.0)
```

Python ще даде `TypeError`, защото `fmin` трябва да се подаде по име.

Защо е полезно? Защото parameters като `fmin`, `fmax`, `artifact_z` и `interp_max_samples` са configuration. Ако ги подаваш positional, лесно можеш да объркаш реда им. Keyword-only прави call site-а по-ясен.

```python
fmin: float = 0.5
```

`fmin` е долната граница на `band-pass` filter-а в Hz. Default е `0.5`.

Ако caller не подаде `fmin`, функцията използва `0.5`.

```python
fmax: float = 40.0
```

`fmax` е горната граница на `band-pass` filter-а в Hz. Default е `40.0`.

Така default filter-ът пази честоти между `0.5 Hz` и `40.0 Hz`.

```python
artifact_z: float = 8.0, #?
```

`artifact_z` контролира колко extreme трябва да е един sample, за да бъде маркиран като artifact.

Коментарът `#?` показва, че авторът вероятно е оставил бележка или несигурност. Самият код обаче използва стойността ясно: threshold-ът става `artifact_z * 1.4826 * mad`.

Default `8.0` означава грубо: "маркирай samples, които са повече от 8 robust standard deviations от median-а".

```python
interp_max_samples: int | None = None, #?
```

`interp_max_samples` казва колко дълъг bad run може да се поправи чрез interpolation.

Type hint-ът `int | None` означава: стойността може да е `int` или `None`.

- Ако е `int`, например `100`, short bad runs до 100 samples ще се interpolate-нат.
- Ако е `None`, функцията сама ще изчисли default по-късно: около 2 секунди samples.

Коментарът `#?` отново изглежда като бележка от автора, но не променя behavior-а.

```python
) -> EEGSession:
```

Return type hint: функцията връща `EEGSession`.

Това е важна design идея: input е `EEGSession`, output е нов `EEGSession`.

---

## Docstring на `clean`

```python
    """Band-pass and suppress large artifacts; return a new session.

    - Zero-phase Butterworth band-pass (``fmin``–``fmax`` Hz).
    - Samples with |x - median| > ``artifact_z`` * MAD (per channel) are
      linearly interpolated. Short spikes (cough-like) are removed without
      changing length or channel count.

    Absolute µV thresholds are not used (LYS exports are not calibrated).
    """
```

Това е function docstring. Той описва какво прави `clean`.

Първото изречение:

```text
Band-pass and suppress large artifacts; return a new session.
```

означава: приложи `band-pass` filtering и потисни големи artifacts, после върни нов session.

`band-pass` означава filter, който пази signal components само в определен frequency range. Тук range-ът е от `fmin` до `fmax`.

`Zero-phase Butterworth band-pass`:

- `Butterworth` е вид filter design, известен с smooth frequency response.
- `zero-phase` тук идва от `filtfilt`: signal-ът се filter-ва forward и после backward, което премахва phase delay. Практически peaks не се изместват във времето.

Следващата част:

```text
Samples with |x - median| > artifact_z * MAD (per channel) are linearly interpolated.
```

Това описва artifact detection.

За всеки channel отделно:

1. Взима се `median`.
2. Изчислява се `MAD`, тоест median absolute deviation.
3. Всеки sample `x`, който е твърде далеч от `median`, се счита за `bad`.
4. Bad samples се поправят чрез `linear interpolation`, ако са в кратък run.

`|x - median|` означава absolute distance от median-а.

Важно: docstring казва `artifact_z * MAD`, но кодът реално прави:

```python
artifact_z * 1.4826 * mad
```

Тоест има допълнителен scaling factor `1.4826`. По-долу кодът обяснява това с comment.

```text
without changing length or channel count
```

Това е ключово. Cleaning-ът не трие rows и не трие columns. Ако input `data.shape` е `(5000, 4)`, output `data.shape` остава `(5000, 4)`.

Последното изречение:

```text
Absolute µV thresholds are not used (LYS exports are not calibrated).
```

Тук се казва: кодът не казва "всичко над 100 microvolts е artifact", защото LYS export-ите не са calibrated. Вместо това threshold-ът е relative to each channel's median and MAD.

Факт от файла: няма absolute threshold.  
Assumption от домейна: LYS values може да не са надеждно в true microvolts.

До този момент знаем public contract-а:

```text
input EEGSession
-> copy data
-> filter frequencies
-> fix extreme samples
-> output new EEGSession със същата форма
```

---

## Копиране на data

```python
    x = np.array(session.data, dtype=np.float64, copy=True)
```

Това е първата runtime операция във функцията.

Когато някой извика `clean(session)`, Python влиза във функцията и стига до този ред.

Нека кажем, че:

```python
session.data.shape == (5000, 4)
session.data.dtype == float64
```

`session.data` е input value. Това е original EEG matrix от session-а.

`np.array(...)` получава arguments:

- `session.data`: data source
- `dtype=np.float64`: искаме числата да са 64-bit floating point
- `copy=True`: искаме нов array, не view към стария

Какво прави `np.array` тук:

1. Чете `session.data`.
2. Създава нов `np.ndarray`.
3. Преобразува values към `np.float64`, ако вече не са.
4. Копира values в нов memory buffer.
5. Връща този нов array.

Резултатът се assign-ва на local variable `x`.

След този ред:

```text
x -> нов np.ndarray със същите numbers като session.data
session.data -> остава както си е
```

Това е program state change вътре във функцията: появява се local variable `x`.

Защо е важно `copy=True`? Защото по-надолу кодът ще прави:

```python
x[:, ch] = ...
```

Това променя `x` in place. Ако `x` беше просто reference към `session.data`, щяхме да mutate-нем original session-а. Тук авторът явно иска input session-ът да остане unchanged.

Concrete example:

```text
session.data[2500, 0] = 1000000.0
```

След копирането:

```text
x[2500, 0] = 1000000.0
```

Но ако после променим:

```text
x[2500, 0] = 3.14
```

то:

```text
session.data[2500, 0]
```

си остава `1000000.0`.

---

```python
    fs = session.fs
```

Този ред взима sampling rate от session-а.

`fs` е local variable. Обикновено `fs` означава sampling frequency.

Input:

```python
session.fs
```

Например:

```text
500.0
```

Операцията е simple attribute access. Python взима attribute `fs` от object-а `session`.

Резултатът е number, обикновено `float`.

След този ред:

```text
fs = 500.0
```

Защо ни трябва? Защото filter frequencies `fmin` и `fmax` са в Hz, но `scipy.signal.butter` в този usage очаква normalized frequencies спрямо Nyquist frequency.

---

```python
    nyq = fs / 2.0
```

Този ред изчислява Nyquist frequency.

`Nyquist frequency` е половината от sampling rate. Ако sampling rate е `500 Hz`, най-високата честота, която може да се представи без aliasing, е `250 Hz`.

Input:

```text
fs = 500.0
```

Operation:

```text
500.0 / 2.0
```

Result:

```text
250.0
```

Резултатът се записва в local variable `nyq`.

След този ред:

```text
fs = 500.0
nyq = 250.0
```

Това се използва веднага за normalized cutoff values.

---

```python
    low = max(fmin / nyq, 1e-6)
```

Този ред превръща lower cutoff frequency от Hz към normalized frequency.

Input values:

```text
fmin = 0.5
nyq = 250.0
```

Operation:

```text
fmin / nyq = 0.5 / 250.0 = 0.002
```

После `max(..., 1e-6)` сравнява резултата с `0.000001` и взима по-голямото.

За default example:

```text
max(0.002, 0.000001) = 0.002
```

Резултатът:

```text
low = 0.002
```

Защо има `1e-6`? Защото filter cutoff не трябва да е точно `0`. Ако `fmin` е `0`, `fmin / nyq` ще е `0`, а това може да е invalid за `butter` band-pass filter. Минималната стойност `1e-6` пази кода от нула.

Type на `low` е `float`.

---

```python
    high = min(fmax / nyq, 0.999)
```

Този ред прави същото за upper cutoff frequency.

Input values:

```text
fmax = 40.0
nyq = 250.0
```

Operation:

```text
fmax / nyq = 40.0 / 250.0 = 0.16
```

После:

```text
min(0.16, 0.999) = 0.16
```

Резултат:

```text
high = 0.16
```

Защо има `0.999`? Защото normalized cutoff не трябва да стига `1.0`, което би означавало точно Nyquist frequency. `butter` в този режим очаква values между `0` и `1`.

След тези два реда имаме:

```text
fmin/fmax in Hz -> low/high normalized to Nyquist
```

Concrete data flow:

```text
session.fs = 500.0
fmin = 0.5
fmax = 40.0
nyq = 250.0
low = 0.002
high = 0.16
```

---

```python
    if high <= low:
        raise ValueError(f"invalid band-pass for fs={fs}: {fmin}-{fmax}")
```

Това е validation.

Python първо evaluate-ва condition-а:

```python
high <= low
```

Ако `high` е по-малко или равно на `low`, filter band-ът е invalid. `band-pass` трябва да има lower edge по-нисък от upper edge.

Пример за нормален случай:

```text
low = 0.002
high = 0.16
high <= low -> False
```

Тогава body-то на `if` не се изпълнява и кодът продължава.

Пример за грешен случай:

```text
fmin = 40.0
fmax = 0.5
low = 0.16
high = 0.002
high <= low -> True
```

Тогава се изпълнява:

```python
raise ValueError(...)
```

`raise` прекъсва нормалното изпълнение на функцията и хвърля exception.

`ValueError` е built-in exception type в Python, използван когато value е неподходяща.

`f"invalid band-pass for fs={fs}: {fmin}-{fmax}"` е f-string. Python вкарва текущите стойности на `fs`, `fmin`, `fmax` в текста.

Ако `fs=500.0`, `fmin=40.0`, `fmax=0.5`, message-ът ще е приблизително:

```text
invalid band-pass for fs=500.0: 40.0-0.5
```

Ако exception бъде raised, функцията не стига до filtering и не връща `EEGSession`.

До този момент функцията е подготвила чисто копие на data и е проверила, че filter boundaries са смислени.

---

## Създаване на filter coefficients

```python
    b, a = butter(4, [low, high], btype="band")
```

Тук вече се използва `scipy.signal.butter`.

Arguments:

- `4`: order на filter-а. Това е 4th-order Butterworth filter.
- `[low, high]`: list с normalized lower и upper cutoff frequencies.
- `btype="band"`: казва, че искаме `band-pass` filter.

При default example:

```python
butter(4, [0.002, 0.16], btype="band")
```

Какво прави функцията на API ниво:

1. Design-ва digital Butterworth filter.
2. Изчислява coefficients.
3. Връща два arrays или array-like objects: `b` и `a`.

`b` и `a` са filter coefficients.

В signal processing често digital filter се описва с difference equation. `b` са numerator coefficients, `a` са denominator coefficients.

Точната numerical процедура вътре в `butter` е в SciPy, не в този файл. От този файл не можем да проследим всяко floating-point изчисление вътре.

Python unpacking:

```python
b, a = ...
```

означава: функцията връща iterable с две стойности; първата отива в `b`, втората в `a`.

След този ред:

```text
b -> np.ndarray с filter numerator coefficients
a -> np.ndarray с filter denominator coefficients
```

Тези coefficients се използват веднага от `filtfilt`.

---

```python
    # filtfilt needs enough samples
```

Това е comment. Python го игнорира при execution.

Той казва на човека защо следващият ред съществува: `filtfilt` има нужда от достатъчно samples около краищата на signal-а, защото използва padding.

---

```python
    padlen = min(3 * max(len(a), len(b)), x.shape[0] - 1)
```

Този ред изчислява `padlen`, който ще бъде подаден на `filtfilt`.

Нека го разбием отвътре навън.

```python
len(a)
```

връща броя coefficients в array `a`.

```python
len(b)
```

връща броя coefficients в array `b`.

```python
max(len(a), len(b))
```

взима по-големия от двата броя.

```python
3 * max(...)
```

прави pad length, равен на три пъти по-големия coefficient length. Това съответства на обичаен default style за `filtfilt`.

```python
x.shape[0]
```

`x.shape` е tuple с dimensions на array-а. Ако `x` е shape `(5000, 4)`, тогава:

```text
x.shape[0] = 5000
x.shape[1] = 4
```

`x.shape[0]` е броят samples във времето.

```python
x.shape[0] - 1
```

е maximum padlen, който е по-малък от signal length. За `5000` samples това е `4999`.

Целият ред:

```python
padlen = min(3 * max(len(a), len(b)), x.shape[0] - 1)
```

казва: използвай нормалния pad length, но ако signal-ът е кратък, не позволявай `padlen` да стане по-голям от `n_samples - 1`.

Type на `padlen` е `int`.

Защо? Защото `filtfilt` може да fail-не, ако `padlen` е твърде голям за signal-а.

State след този ред:

```text
x      -> copied EEG data
b, a   -> filter coefficients
padlen -> integer за edge padding
```

---

## Прилагане на filter-а channel по channel

```python
    for ch in range(x.shape[1]):
```

Това започва `for` loop.

`x.shape[1]` е броят columns, тоест броят channels. За валиден `EEGSession` това е `4`.

```python
range(4)
```

произвежда sequence:

```text
0, 1, 2, 3
```

На всяка iteration Python assign-ва следващата стойност на local variable `ch`.

Тоест loop-ът ще мине през всеки channel index.

---

```python
        x[:, ch] = filtfilt(b, a, x[:, ch], padlen=padlen)
```

Това е един от най-важните редове във файла.

Да го разбием.

```python
x[:, ch]
```

е NumPy slicing.

`:` за first dimension означава "всички rows", тоест всички samples.

`ch` за second dimension означава "само column с index `ch`", тоест един EEG channel.

Ако `x.shape == (5000, 4)` и `ch == 2`, тогава:

```python
x[:, 2]
```

е 1-D array с shape `(5000,)`, съдържащ всички samples за channel 2.

Сега function call-ът:

```python
filtfilt(b, a, x[:, ch], padlen=padlen)
```

Arguments:

- `b`: numerator filter coefficients от `butter`
- `a`: denominator filter coefficients от `butter`
- `x[:, ch]`: 1-D signal за текущия channel
- `padlen=padlen`: keyword argument, който казва колко padding да използва в краищата

Runtime behavior:

1. Python evaluate-ва `b`.
2. Evaluate-ва `a`.
3. Evaluate-ва `x[:, ch]`, което взима текущия channel като 1-D array/view.
4. Evaluate-ва `padlen`.
5. Влиза в `scipy.signal.filtfilt`.
6. SciPy прилага filter-а forward и backward.
7. `filtfilt` връща filtered 1-D `np.ndarray` със същата дължина като input signal-а.

Резултатът после се assign-ва обратно:

```python
x[:, ch] = returned_array
```

Това променя `x` in place. Само column `ch` се overwrite-ва с filtered values.

Concrete example:

```text
before:
x[:, 0] = raw AF4 signal

operation:
filtered_ch0 = filtfilt(b, a, x[:, 0], padlen=padlen)

after:
x[:, 0] = filtered_ch0
```

После loop-ът продължава с `ch = 1`, после `ch = 2`, после `ch = 3`.

След целия loop:

```text
x contains band-pass filtered data for all 4 channels
session.data is still unchanged
```

Защо filter-ваме per channel? Защото всяка EEG electrode/channel е отделен time series. `filtfilt` тук е извикан върху 1-D array, не върху цялата 2-D matrix наведнъж.

До този момент имаме:

```text
original session.data
-> copied into x
-> each channel in x filtered between fmin and fmax
```

---

## Default за `interp_max_samples`

```python
    if interp_max_samples is None:
        interp_max_samples = int(round(2.0 * fs))  # up to ~2 s bursts
```

След filtering започва artifact handling.

Първо кодът решава каква да е максималната дължина на bad run, който ще се поправя чрез interpolation.

Condition:

```python
interp_max_samples is None
```

`is None` проверява дали variable-ът сочи точно към singleton object-а `None`.

Ако caller е извикал:

```python
clean(session)
```

тогава default value е:

```text
interp_max_samples = None
```

Condition-ът е `True`, така че тялото се изпълнява.

```python
round(2.0 * fs)
```

Ако `fs = 500.0`:

```text
2.0 * 500.0 = 1000.0
round(1000.0) = 1000
```

После:

```python
int(...)
```

гарантира, че резултатът е `int`.

Значи:

```text
interp_max_samples = 1000
```

Коментарът:

```python
# up to ~2 s bursts
```

обяснява intent-а: ако sampling rate е `fs` samples per second, тогава `2.0 * fs` samples са около 2 секунди.

Ако caller вече е подал value:

```python
clean(session, interp_max_samples=50)
```

тогава condition-ът е `False` и `interp_max_samples` остава `50`.

Program state change: local variable `interp_max_samples` може да се промени от `None` към integer.

---

## Artifact detection per channel

```python
    for ch in range(x.shape[1]):
```

Започва втори loop по channels.

Първият loop filter-на channels. Този втори loop търси artifacts в filtered signal-а.

Отново при shape `(n_samples, 4)`:

```text
ch = 0
ch = 1
ch = 2
ch = 3
```

---

```python
        col = x[:, ch]
```

Тук `col` става current channel.

Input:

```python
x[:, ch]
```

Това е 1-D NumPy view или array-like slice към column-а.

Важно: при NumPy slicing, `x[:, ch]` обикновено е view към `x`, не independent copy. Това значи, че `col` гледа към същите values в memory. В този block обаче кодът не променя `col` директно до call-а на `_interp_mask`; той го използва за calculations.

Type:

```text
col: np.ndarray
shape: (n_samples,)
```

Пример:

```text
col = filtered values for channel AF4
```

Резултатът от този ред отива в local variable `col`.

---

```python
        med = np.median(col)
```

Това изчислява median на текущия channel.

Input:

```python
col
```

1-D array от filtered samples.

`np.median(col)`:

1. Взима всички values в `col`.
2. Намира средната по ред стойност, ако values бъдат sorted.
3. Връща scalar number.

Median е robust center. Ако има един огромен spike, median-а почти не се влияе.

Пример:

```text
col = [1.0, 1.1, 0.9, 1000000.0, 1.2]
median = 1.1
```

Ако ползвахме mean, огромният spike щеше да изкриви center-а силно. Median е по-стабилен за artifact detection.

Type на `med` обикновено е `np.float64`.

---

```python
        mad = np.median(np.abs(col - med))
```

Това изчислява `MAD`, median absolute deviation.

Нека го разбием отвътре навън.

```python
col - med
```

NumPy прави broadcasting: scalar `med` се subtract-ва от всеки element на `col`.

Ако:

```text
col = [1.0, 1.1, 0.9, 1000000.0, 1.2]
med = 1.1
```

тогава:

```text
col - med = [-0.1, 0.0, -0.2, 999998.9, 0.1]
```

После:

```python
np.abs(...)
```

взима absolute value element-wise:

```text
[0.1, 0.0, 0.2, 999998.9, 0.1]
```

После:

```python
np.median(...)
```

взима median на тези distances:

```text
median([0.1, 0.0, 0.2, 999998.9, 0.1]) = 0.1
```

Значи:

```text
mad = 0.1
```

Type: scalar, обикновено `np.float64`.

Защо го правим? `MAD` измерва typical distance от median-а, без да позволява на huge outliers да доминират.

Data flow до тук за един channel:

```text
filtered col
-> median center med
-> absolute distances from med
-> median of distances = mad
```

---

```python
        if mad <= 0:
            continue
```

Това е guard.

Ако `mad <= 0`, значи typical deviation е zero или invalidly non-positive.

Пример:

```text
col = [5.0, 5.0, 5.0, 5.0]
med = 5.0
abs(col - med) = [0.0, 0.0, 0.0, 0.0]
mad = 0.0
```

Ако `mad` е zero, threshold-ът:

```python
artifact_z * 1.4826 * mad
```

ще стане `0`. Тогава detection-ът може да стане meaningless. Вместо това кодът казва: този channel няма useful spread за threshold; skip-ваме artifact correction за него.

`continue` означава: прекрати текущата iteration на loop-а и премини към следващия `ch`.

Ако `mad <= 0`, следващите редове за threshold, bad mask и interpolation не се изпълняват за този channel.

Program state: `x` не се променя за този channel в artifact phase.

---

```python
        # consistent with approx normal: sigma ≈ 1.4826 * MAD
```

Това е comment.

Идеята: ако data е приблизително normally distributed, `MAD` може да се превърне към estimate на standard deviation чрез factor `1.4826`.

Technical term-ите тук:

- `sigma` често означава standard deviation.
- `MAD` е median absolute deviation.

Коментарът не се изпълнява, но обяснява защо следващият ред умножава по `1.4826`.

---

```python
        thr = artifact_z * 1.4826 * mad
```

Това изчислява threshold за artifact detection.

Input values:

```text
artifact_z = 8.0
mad = например 0.1
```

Operation:

```text
1.4826 * mad = 0.14826
artifact_z * 0.14826 = 1.18608
```

Result:

```text
thr = 1.18608
```

Meaning:

```text
sample е bad, ако е повече от 1.18608 units далеч от median-а
```

При реални EEG values числата ще са други.

Type: float-like scalar.

Защо threshold-ът е per channel? Защото всеки channel може да има различен scale и noise level. Ако един channel е naturally по-шумен, неговият `mad` ще е по-голям и threshold-ът също ще е по-голям.

---

```python
        bad = np.abs(col - med) > thr
```

Тук се създава boolean mask.

Отново:

```python
col - med
```

дава distance with sign от median-а.

```python
np.abs(col - med)
```

дава absolute distance.

```python
... > thr
```

сравнява всеки element с threshold-а.

Резултатът е `np.ndarray` от booleans, със същата дължина като `col`.

Пример:

```text
col distances = [0.1, 0.0, 0.2, 999998.9, 0.1]
thr = 1.18608

bad = [False, False, False, True, False]
```

Този boolean array казва кои samples са artifacts според текущия channel threshold.

Type:

```text
bad: np.ndarray
bad.dtype == bool
bad.shape == (n_samples,)
```

Program state: появява се local variable `bad`.

---

```python
        if not np.any(bad):
            continue
```

`np.any(bad)` проверява дали има поне един `True` в boolean array-а.

Ако всички са `False`:

```text
np.any(bad) -> False
not False -> True
```

Тогава `continue` skip-ва interpolation за този channel и loop-ът отива към следващия.

Ако има поне един artifact:

```text
np.any(bad) -> True
not True -> False
```

Тогава кодът продължава към `_interp_mask`.

Защо това съществува? За performance и clarity. Ако няма bad samples, няма нужда да call-ваме helper функцията.

---

```python
        x[:, ch] = _interp_mask(col, bad, max_run=interp_max_samples)
```

Тук се поправя текущият channel.

Function call:

```python
_interp_mask(col, bad, max_run=interp_max_samples)
```

Arguments:

- `col`: текущият 1-D signal за channel-а
- `bad`: boolean mask, където `True` означава artifact sample
- `max_run=interp_max_samples`: maximum length на continuous bad segment, който ще се interpolate-не

`max_run` е keyword-only parameter в `_interp_mask`, защото signature-ът там също има `*`.

Runtime:

1. Python evaluate-ва `col`.
2. Evaluate-ва `bad`.
3. Evaluate-ва `interp_max_samples`.
4. Влиза във функцията `_interp_mask`.
5. `_interp_mask` връща нов 1-D `np.ndarray`.
6. Този return value се assign-ва обратно в `x[:, ch]`.

Program state change:

```text
x[:, ch] преди -> filtered signal with artifacts
x[:, ch] след  -> filtered signal with artifacts corrected
```

Важно: `_interp_mask` не променя shape. Ако `col` е length `5000`, returned array също е length `5000`.

След втория channel loop:

```text
x contains filtered data, with artifacts corrected per channel
```

---

```python
    return session.replace(data=x)
```

Това е краят на public function `clean`.

`session.replace(data=x)` е method call върху `session`.

Какво е method? Method е function, която е свързана с object. Когато пишем:

```python
session.replace(data=x)
```

Python реално подава `session` като `self` вътре в method-а `replace`.

От `common.session.EEGSession` се вижда, че `replace` прави приблизително това:

1. Създава dictionary `base` с текущите fields на session-а.
2. Update-ва този dictionary с подадените `kwargs`.
3. Връща `EEGSession(**base)`.

Тук подаваме само:

```python
data=x
```

Значи:

```text
new data       -> cleaned x
fs             -> same as old session.fs
ch_names       -> same
time           -> same
subject_id     -> same
study_id       -> same
phases         -> same
source_path    -> same
```

Return value на `session.replace(data=x)` е нов `EEGSession` instance.

После `return` връща този нов object към caller-а.

Ако caller е написал:

```python
out = clean(session)
```

тогава:

```text
out -> new EEGSession with cleaned data
session -> original EEGSession unchanged
```

Data flow за цялата `clean` функция:

```text
session.data
-> np.array(..., copy=True)
-> x
-> Butterworth band-pass per channel
-> artifact threshold per channel
-> _interp_mask for channels with bad samples
-> session.replace(data=x)
-> returned EEGSession
```

До този момент public part-ът на файла е готов. Остава helper функцията `_interp_mask`, която реално решава как точно да поправи bad samples.

---

## Helper функцията `_interp_mask`

```python
def _interp_mask(col: np.ndarray, bad: np.ndarray, *, max_run: int) -> np.ndarray:
```

Тук се дефинира helper function.

Името започва с underscore: `_interp_mask`. В Python това е convention, че функцията е internal/private за module-а. Не е истинска забрана; друг code може да я import-не, но авторът казва: "Това е helper, public API-то е `clean`."

Signature:

```python
col: np.ndarray
```

`col` е 1-D array за един channel.

```python
bad: np.ndarray
```

`bad` е boolean mask със същата дължина като `col`.

```python
*, max_run: int
```

`max_run` е keyword-only integer. Трябва да се подаде като:

```python
_interp_mask(col, bad, max_run=1000)
```

не като:

```python
_interp_mask(col, bad, 1000)
```

```python
) -> np.ndarray:
```

Функцията връща `np.ndarray`.

Тази helper функция не знае нищо за `EEGSession`. Тя работи само с един vector `col` и mask `bad`.

---

```python
    """Interpolate bad samples; leave long bad runs unchanged (masked as med)."""
```

Docstring на helper функцията.

Той казва: interpolate-ни bad samples; long bad runs не се interpolate-ват от neighbors, а се mask-ват като median.

Има малка неточност във wording-а: "leave long bad runs unchanged" звучи сякаш ще останат същите values, но в кода long bad runs се set-ват към median на good samples:

```python
out[long_bad] = float(np.median(col[good]))
```

Така че фактът от кода е: long bad runs се replaced с median, не се оставят unchanged.

---

```python
    out = col.copy()
```

Това създава working copy на input channel-а.

Input:

```python
col
```

Operation:

```python
col.copy()
```

Result:

```text
out -> new np.ndarray със същите values като col
```

Защо copy? Защото функцията ще променя selected positions. Ако променяше `col` директно, можеше да mutate-не data outside helper-а. С copy функцията build-ва output array контролирано.

---

```python
    n = len(col)
```

Това взима броя samples в channel-а.

Ако:

```text
col.shape == (5000,)
```

тогава:

```text
len(col) == 5000
```

Result:

```text
n = 5000
```

Type: `int`.

`n` се използва в loops и за създаване на masks със същата дължина.

---

```python
    good = ~bad
```

Това създава inverse mask.

`~` върху boolean NumPy array означава element-wise logical NOT.

Ако:

```text
bad = [False, False, True, True, False]
```

тогава:

```text
good = [True, True, False, False, True]
```

Meaning:

- `bad[i] == True` означава sample `i` е artifact.
- `good[i] == True` означава sample `i` не е artifact.

Type:

```text
good: np.ndarray
good.dtype == bool
good.shape == bad.shape
```

Този mask ще се използва като anchor points за interpolation.

---

```python
    if not np.any(good):
        return out
```

Това е edge case.

`np.any(good)` проверява дали има поне един `True` в `good`.

Ако няма нито един good sample, значи всички samples са bad.

Пример:

```text
bad  = [True, True, True]
good = [False, False, False]
```

Тогава няма reliable neighbor values, от които да interpolate-нем.

Кодът прави:

```python
return out
```

`out` в този момент е copy на original `col`, без промени.

Така функцията казва: ако всичко е bad, не мога да поправя нищо от налична good информация, затова връщам copy as-is.

Това е факт от кода. Дали това е най-доброто signal-processing поведение е design decision извън този файл.

Ако има поне един good sample, кодът продължава.

---

## Намиране на дълги bad runs

```python
    # mark runs longer than max_run as "don't interp from neighbors" → set to median of good
```

Това е comment.

`run` тук означава continuous sequence от bad samples.

Пример:

```text
bad = [False, True, True, False, True, True, True, False]
```

Имаме два bad runs:

```text
indices 1..2 -> length 2
indices 4..6 -> length 3
```

Ако `max_run = 2`, първият run може да се interpolate-не, но вторият е too long и ще се mark-не като `long_bad`.

Коментарът казва: runs по-дълги от `max_run` няма да се interpolate-ват от neighbors; те ще се set-нат към median на good samples.

---

```python
    i = 0
```

Това създава loop index `i`.

Meaning:

```text
i -> current position while scanning through samples
```

Започваме от първия sample, index `0`.

---

```python
    long_bad = np.zeros(n, dtype=bool)
```

Това създава boolean mask за long bad runs.

Arguments:

- `n`: length на array-а
- `dtype=bool`: values са booleans

Ако `n = 8`:

```text
long_bad = [False, False, False, False, False, False, False, False]
```

Initially никой sample не е marked като long bad.

По-късно, ако кодът намери bad run с length > `max_run`, ще set-не съответния slice към `True`.

---

```python
    while i < n:
```

Това започва `while` loop.

`while` изпълнява body-то докато condition-ът е `True`.

Condition:

```python
i < n
```

Значи: продължавай да scan-ваш, докато `i` е valid index в array-а.

Ако `n = 8`, valid indices са `0` до `7`. Когато `i` стане `8`, loop-ът приключва.

Този loop scan-ва `bad` отляво надясно.

---

```python
        if not bad[i]:
            i += 1
            continue
```

Това проверява дали current sample не е bad.

`bad[i]` е boolean за sample at index `i`.

Ако:

```text
bad[i] == False
```

тогава:

```text
not bad[i] == True
```

Body-то се изпълнява.

```python
i += 1
```

е shorthand за:

```python
i = i + 1
```

Тоест move-ваме scanner-а към следващия sample.

```python
continue
```

казва: прескочи остатъка от body-то на `while` loop-а и започни следващата iteration.

Meaning: ако current sample е good, няма bad run започващ тук. Просто върви напред.

Program state change: `i` се увеличава с 1.

---

```python
        j = i
```

Този ред се изпълнява само ако `bad[i]` е `True`. Тоест намерили сме начало на bad run.

`j` ще бъде second pointer, който върви напред, докато bad run-ът свърши.

Initial state:

```text
i = start index на bad run
j = same start index
```

---

```python
        while j < n and bad[j]:
            j += 1
```

Този inner `while` loop намира края на continuous bad run.

Condition:

```python
j < n and bad[j]
```

`and` означава: и двете условия трябва да са `True`.

Python evaluate-ва отляво надясно. Първо `j < n`. Ако това е `False`, Python не evaluate-ва `bad[j]`, което предпазва от out-of-bounds access.

Докато `j` е в array-а и `bad[j]` е `True`, loop-ът прави:

```python
j += 1
```

Тоест мести `j` надясно.

Пример:

```text
bad = [False, True, True, True, False]
```

Ако `i = 1`:

```text
j = 1 -> bad[1] True -> j = 2
j = 2 -> bad[2] True -> j = 3
j = 3 -> bad[3] True -> j = 4
j = 4 -> bad[4] False -> stop
```

След loop-а:

```text
i = 1
j = 4
bad run covers indices 1, 2, 3
slice is i:j, meaning 1:4
length is j - i = 3
```

Python slices са end-exclusive. `i:j` включва `i`, но не включва `j`.

---

```python
        if (j - i) > max_run:
            long_bad[i:j] = True
```

Тук се решава дали намереният bad run е too long.

```python
j - i
```

е length на run-а.

Ако:

```text
i = 1
j = 4
```

тогава:

```text
j - i = 3
```

Condition:

```python
(j - i) > max_run
```

Ако run length е строго по-голяма от `max_run`, маркираме run-а като long bad.

Пример:

```text
max_run = 2
run length = 3
3 > 2 -> True
```

Тогава:

```python
long_bad[i:j] = True
```

set-ва всички positions от `i` до `j - 1` в `long_bad` на `True`.

Ако:

```text
long_bad = [False, False, False, False, False]
i = 1
j = 4
```

след assignment:

```text
long_bad = [False, True, True, True, False]
```

Ако run length е equal to `max_run`, не е long. Условието е `>`, не `>=`.

---

```python
        i = j
```

След като сме обработили bad run-а, преместваме outer scanner-а `i` до края на run-а.

Ако run-ът е бил `1:4`, след това:

```text
i = 4
```

Следващата iteration на outer `while` ще започне от първия sample след bad run-а.

Така кодът не scan-ва същите bad samples повторно.

След приключване на целия `while i < n` loop:

```text
long_bad[i] == True  за samples, които са част от bad run по-дълъг от max_run
long_bad[i] == False за всичко останало
```

До този момент `_interp_mask` е класифицирала bad samples на две групи:

```text
bad short runs -> eligible for interpolation
bad long runs  -> set to median of good
```

---

## Разделяне на short bad и long bad samples

```python
    interp_bad = bad & ~long_bad
```

Това създава mask за bad samples, които трябва да се interpolate-нат.

Operators:

- `~long_bad`: inverse на long_bad
- `bad & ...`: element-wise logical AND

Meaning:

```text
interp_bad е True там, където:
sample е bad
и sample не е част от long_bad run
```

Пример:

```text
bad       = [False, True, True, False, True, True, True, False]
long_bad  = [False, False, False, False, True, True, True, False]
~long_bad = [True, True, True, True, False, False, False, True]

interp_bad = bad & ~long_bad
           = [False, True, True, False, False, False, False, False]
```

Така short run-ът на indices `1,2` ще се interpolate-не, а long run-ът `4,5,6` няма.

---

```python
    idx = np.arange(n)
```

Това създава array от indices.

Ако `n = 8`:

```text
idx = [0, 1, 2, 3, 4, 5, 6, 7]
```

Type:

```text
idx: np.ndarray
idx.dtype: integer type
idx.shape: (n,)
```

Защо е нужен? `np.interp` работи с x-coordinates и y-values. Тук x-coordinate-ите са sample indices във времето.

Ментален модел:

```text
sample index -> signal value
0 -> col[0]
1 -> col[1]
2 -> col[2]
...
```

---

```python
    if np.any(interp_bad):
        out[interp_bad] = np.interp(idx[interp_bad], idx[good], col[good])
```

Това поправя short bad samples чрез linear interpolation.

Първо condition:

```python
np.any(interp_bad)
```

Ако няма samples за interpolation, body-то се skip-ва.

Ако има поне един `True`, се изпълнява assignment-ът.

Нека разбием right side:

```python
idx[interp_bad]
```

Това избира indices на samples, които искаме да поправим.

Пример:

```text
idx        = [0, 1, 2, 3, 4]
interp_bad = [False, False, True, False, False]

idx[interp_bad] = [2]
```

```python
idx[good]
```

Това избира indices на good samples.

```python
col[good]
```

Това избира values на good samples.

`np.interp(x, xp, fp)` на API ниво прави 1-D linear interpolation:

- `x`: positions, за които искаме estimated values
- `xp`: known x positions
- `fp`: known y values at those positions

Тук:

```python
np.interp(idx[interp_bad], idx[good], col[good])
```

означава:

```text
За всеки bad sample index, изчисли value по права линия между surrounding good samples.
```

Concrete example:

```text
col  = [10.0, 12.0, 999.0, 16.0, 18.0]
bad  = [False, False, True, False, False]
good = [True, True, False, True, True]
idx  = [0, 1, 2, 3, 4]

idx[interp_bad] = [2]
idx[good]       = [0, 1, 3, 4]
col[good]       = [10.0, 12.0, 16.0, 18.0]
```

За index `2`, най-близките known points са:

```text
index 1 -> value 12.0
index 3 -> value 16.0
```

Linear interpolation по средата дава:

```text
14.0
```

`np.interp(...)` връща array:

```text
[14.0]
```

Лявата страна:

```python
out[interp_bad] = ...
```

assign-ва тези interpolated values само на positions, където `interp_bad` е `True`.

След assignment:

```text
out = [10.0, 12.0, 14.0, 16.0, 18.0]
```

Program state change: `out` се променя in place at short bad sample positions.

Важно: `col` не се променя тук. Променя се `out`, който е copy.

Ако short bad run е в началото или края на signal-а, `np.interp` има своето API поведение за values outside known range: използва boundary values. Това поведение идва от NumPy, не е custom code тук.

---

```python
    if np.any(long_bad):
        out[long_bad] = float(np.median(col[good]))
```

Това обработва long bad runs.

Първо:

```python
np.any(long_bad)
```

проверява дали има поне един sample, маркиран като long bad.

Ако няма, body-то се skip-ва.

Ако има, right side се evaluate-ва:

```python
col[good]
```

избира values на good samples.

```python
np.median(col[good])
```

намира median на good values.

```python
float(...)
```

превръща NumPy scalar към Python `float`.

После:

```python
out[long_bad] = that_float
```

set-ва всички long bad positions към една и съща стойност: median на good samples.

Concrete example:

```text
col      = [10.0, 12.0, 999.0, 999.0, 999.0, 18.0]
bad      = [False, False, True, True, True, False]
max_run  = 2
long_bad = [False, False, True, True, True, False]
good     = [True, True, False, False, False, True]

col[good] = [10.0, 12.0, 18.0]
median    = 12.0

out[long_bad] = 12.0
```

Result:

```text
out = [10.0, 12.0, 12.0, 12.0, 12.0, 18.0]
```

Защо не interpolate-ваме long bad runs? Ако artifact segment е твърде дълъг, linear interpolation между далечни neighbors може да измисли smooth signal, който изглежда прекалено уверен. Тук design choice-ът е: за дълъг corrupted segment, използвай neutral robust value, median на good samples.

Това запазва length-а и избягва huge spikes, но не възстановява истински brain signal. Това е важно epistemically: code-ът suppress-ва artifact, не доказва какъв е бил original signal.

---

```python
    return out
```

Това връща поправения channel array.

Return value:

```text
out: np.ndarray
shape: same as col
```

Какво съдържа:

- original `col` values за samples, които не са bad
- interpolated values за short bad samples
- median-of-good за long bad samples

Този return value се връща към мястото, където `_interp_mask` е извикана:

```python
x[:, ch] = _interp_mask(col, bad, max_run=interp_max_samples)
```

След това `clean` записва returned `out` обратно в съответния channel на `x`.

С това helper функцията приключва, а с нея и целият file.

---

## Пълна runtime картина с пример

Да проследим един simplified example.

Имаме session:

```text
session.data.shape = (5000, 4)
session.fs = 500.0
fmin = 0.5
fmax = 40.0
artifact_z = 8.0
interp_max_samples = None
```

Caller прави:

```python
cleaned = clean(session)
```

Python влиза в `clean`.

Първо:

```text
session.data -> copied to x as float64
```

После:

```text
fs = 500.0
nyq = 250.0
low = 0.5 / 250.0 = 0.002
high = 40.0 / 250.0 = 0.16
```

Validation:

```text
high <= low -> False
```

Filter design:

```text
butter(4, [0.002, 0.16], btype="band")
-> b, a
```

Filtering:

```text
for each channel:
    x[:, ch] -> filtfilt -> filtered values -> x[:, ch]
```

Artifact setup:

```text
interp_max_samples is None
-> interp_max_samples = round(2.0 * 500.0) = 1000
```

Artifact correction for each channel:

```text
col = x[:, ch]
med = median(col)
mad = median(abs(col - med))
if mad <= 0: skip
thr = 8.0 * 1.4826 * mad
bad = abs(col - med) > thr
if no bad: skip
otherwise:
    _interp_mask(col, bad, max_run=1000)
    -> corrected channel
    -> write back into x[:, ch]
```

Return:

```text
session.replace(data=x)
-> new EEGSession
-> cleaned
```

Original `session` остава unchanged. New `cleaned` object има същите `fs`, `time`, `ch_names`, `subject_id`, `study_id`, `phases`, но different `data`.

---

## Control-flow paths, които файлът има

Има няколко възможни пътя през кода.

Normal path:

```text
valid filter band
enough valid data for filtfilt
for each channel:
    mad > 0
    maybe bad samples
return new EEGSession
```

Invalid band path:

```text
high <= low
-> raise ValueError
-> no return value
```

Flat channel path:

```text
mad <= 0
-> continue
-> artifact correction skipped for that channel
```

No artifacts path:

```text
np.any(bad) == False
-> continue
-> channel stays only band-pass filtered
```

All samples bad inside `_interp_mask`:

```text
np.any(good) == False
-> return out copy unchanged
```

Short bad run path:

```text
bad run length <= max_run
-> interp_bad True
-> np.interp
-> replace those samples with interpolated values
```

Long bad run path:

```text
bad run length > max_run
-> long_bad True
-> set those samples to median(col[good])
```

Potential external failure path:

```text
filtfilt(...)
```

може да raise exception, ако input signal или parameters са неподходящи. Точните rules са в SciPy. Този файл частично се пази чрез `padlen`, но не съдържа собствен `try/except`.

---

## Какво този файл променя и какво не променя

Променя:

- local array `x`
- per-channel values inside `x`
- local helper output `out`
- returned `EEGSession` има cleaned `data`

Не променя:

- original `session.data`, защото `x` е copy
- броя samples
- броя channels
- `fs`
- `time`
- `ch_names`
- `subject_id`
- `study_id`
- `phases`
- `source_path`

---

## Какви concepts научихме от този файл

`EEGSession` е project object, който държи EEG recording и metadata.

`np.ndarray` е основната data structure за numerical arrays.

`sampling rate` (`fs`) казва колко samples има за една секунда.

`Nyquist frequency` е `fs / 2`.

`band-pass` filter пази frequency band между `fmin` и `fmax`.

`butter` design-ва Butterworth filter coefficients.

`filtfilt` прилага filter forward и backward, за да избегне phase shift.

`median` и `MAD` са robust statistics, полезни при outliers.

`boolean mask` е array от `True`/`False`, с който избираме positions в NumPy array.

`linear interpolation` estimating-ва missing/bad values между good neighbors.

`keyword-only arguments` се задават след `*` и трябва да се подават по име.

`return session.replace(data=x)` създава нов `EEGSession` със сменено поле `data`.

---

## Кратко финално обобщение

`src/clean/pipeline.py` дефинира една public функция `clean(session, ...)` и една internal helper функция `_interp_mask(...)`.

`clean` приема `EEGSession`, копира неговата `data`, изчислява normalized filter boundaries, създава Butterworth `band-pass` filter, filter-ва всеки channel с `filtfilt`, после за всеки channel намира extreme samples чрез `median` и `MAD`. Ако намери artifacts, подава channel-а и boolean mask към `_interp_mask`.

`_interp_mask` разделя bad samples на short bad runs и long bad runs. Short bad runs се поправят чрез `np.interp`, а long bad runs се set-ват към median на good samples. Накрая връща cleaned 1-D array за channel-а.

Накрая `clean` връща нов `EEGSession` чрез `session.replace(data=x)`. Така pipeline-ът получава cleaned session със същата структура и metadata, но с обработена signal matrix.

---

## Проверка, че не сме пропуснали важна част

Покрихме:

- module docstring
- `from __future__ import annotations`
- `numpy` import
- `scipy.signal.butter` и `scipy.signal.filtfilt` imports
- `EEGSession` import и какво представлява object-ът
- пълния signature на `clean`
- keyword-only `*`
- всички default parameters
- return type hint
- function docstring на `clean`
- копирането на `session.data`
- `fs`, `nyq`, `low`, `high`
- validation и `ValueError`
- `butter(...)`
- `padlen`
- първия channel loop с `filtfilt`
- default logic за `interp_max_samples`
- втория channel loop
- `col`, `med`, `mad`
- guard при `mad <= 0`
- threshold `thr`
- boolean mask `bad`
- guard при липса на bad samples
- call към `_interp_mask`
- `session.replace(data=x)`
- signature и docstring на `_interp_mask`
- `out`, `n`, `good`
- edge case, когато няма good samples
- scanning loop с `i` и `j`
- detection на long bad runs
- `interp_bad`
- `idx`
- `np.interp`
- replacement на long bad samples с median
- final `return out`
- всички основни control-flow paths
- input/output и state changes на всяка meaningful част

С други думи: няма важна функция, class usage, operation, return statement, branch или data-flow step от `pipeline.py`, която да е пропусната.
