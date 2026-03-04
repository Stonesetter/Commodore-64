# BSDBASIC — Changelog

## Version 1.1 (Current)

### Bug Fixes

**Sine wave / all math functions broken (silent crash)**
- Root cause: The math function dispatcher (`SIN`, `COS`, `TAN`, `ATN`, `EXP`,
  `LOG`, `SQR`, `ABS`, `INT`) used `new RegExp('^SIN(')` in JavaScript, which
  put an unescaped `(` into a regex pattern, creating an invalid expression.
  Every call to a math function threw a JavaScript exception that was silently
  swallowed, returning 0 each time. Sine wave drew nothing; any program using
  math functions produced wrong results.
- Fix: Replaced the regex-based `matchKw` with a new `matchKwLP` method using
  plain `startsWith()` checks. No regex involved. Applied to all math functions
  (`SIN`, `COS`, `TAN`, etc.) and all string functions (`CHR$`, `STR$`,
  `LEFT$`, `RIGHT$`, `MID$`, `STRING$`).

**FOR/NEXT loop termination caused infinite loop then crash**
- Root cause: When a FOR/NEXT loop completed its final iteration, the code set
  `jumped = true` unconditionally. This prevented the outer `li++` from
  advancing past the NEXT line, so the interpreter re-executed NEXT, found no
  matching FOR frame (it had been popped), and crashed with
  `?NEXT WITHOUT FOR`.
- Fix: `jumped = true` is only set when the loop is continuing (not done).
  When the loop is done, the FOR frame is removed and `jumped` remains false,
  allowing `li++` to naturally advance past NEXT.

**Countdown printed all numbers on one line**
- Root cause: The sample program used `PRINT I;"..."` with a trailing
  semicolon, which suppresses the newline, causing all numbers to run together.
- Fix: Changed to `PRINT I;"..."` without trailing semicolon so each number
  appears on its own line. Also halved SLEEP to 30 ticks (0.5s) for a more
  satisfying countdown pace.

**String functions with `$` in name matched incorrectly**
- Root cause: Functions like `CHR$`, `STR$`, `LEFT$` were being matched with
  `new RegExp('^CHR\\$')` which is fragile and breaks in some JS engines.
- Fix: All string function matching now uses `matchKwLP` (startsWith-based),
  which handles the `$` character naturally without regex escaping.

---

## Version 1.0 (Initial Release)

- Full CBM BASIC V2 interpreter in Python (terminal) and JavaScript (browser)
- Statements: PRINT, INPUT, LET, IF/THEN/ELSE, FOR/NEXT/STEP, GOTO, GOSUB,
  RETURN, ON/GOTO, ON/GOSUB, DIM, DATA, READ, RESTORE, END, STOP, CLR, CLS,
  SLEEP, REM, POKE (stub)
- Numeric functions: SIN, COS, TAN, ATN, EXP, LOG, SQR, ABS, INT, SGN, RND, PEEK
- String functions: LEN, LEFT$, RIGHT$, MID$, CHR$, ASC, STR$, VAL, STRING$
- Print formatting: TAB(), SPC(), semicolon, comma print zones
- Operators: +, -, *, /, ^, <, >, =, <>, <=, >=, AND, OR, NOT
- Python version: readline history, ANSI colour output, SAVE/LOAD/DIR commands
- Browser version: C64-style colour scheme, on-screen keyboard, keyword bar,
  8 built-in sample programs
