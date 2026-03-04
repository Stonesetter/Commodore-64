# BSDBASIC — Language Reference

Complete reference for all statements, functions, and operators supported
by the BSDBASIC interpreter (both basic.py and basic.html).

---

## Program Structure

Every line in a BASIC program begins with a **line number** (1–65535), followed
by one or more statements separated by colons:

```
10 REM THIS IS A COMMENT
20 A=5 : B=10 : PRINT A+B
30 END
```

Lines are executed in ascending numeric order. Gaps between numbers let you
insert lines later:

```
10 PRINT "FIRST"
20 PRINT "SECOND"
15 PRINT "INSERTED BETWEEN 10 AND 20"
```

After `LIST`, the order will be 10, 15, 20.

---

## Variables

### Numeric Variables

Any name starting with a letter, followed by letters or digits:

```
A = 3.14
SCORE = 0
X2 = 100
```

All numeric variables hold floating-point values (IEEE 754 double).

### String Variables

Same naming rules but the name **must end with `$`**:

```
A$ = "HELLO"
NAME$ = "BIG DADDY BEAR"
```

### Multiple Statements Per Line

Use `:` to put multiple statements on one line:

```
10 A=1 : B=2 : C=A+B : PRINT C
```

---

## Statements

### REM
Comment — everything after REM is ignored.
```
10 REM THIS IS A COMMENT
```

### LET
Assign a value to a variable. The `LET` keyword is optional.
```
10 LET A = 5
20 B = 10        : REM LET is implied
30 A$ = "HELLO"
```

### PRINT
Output values to the screen.
```
PRINT "HELLO"
PRINT A
PRINT "X ="; X
PRINT A, B, C         : REM comma = jump to next 14-col zone
PRINT "NO NEWLINE";   : REM trailing semicolon suppresses newline
PRINT                  : REM blank line
```

**TAB(n)** — move to column n before printing:
```
PRINT TAB(10); "INDENTED"
```

**SPC(n)** — print n spaces:
```
PRINT "A"; SPC(5); "B"
```

### INPUT
Read user input into one or more variables:
```
INPUT A
INPUT "ENTER YOUR NAME"; N$
INPUT "X,Y = "; X, Y
```
If multiple variables are listed, the user may separate values with commas.

### IF / THEN / ELSE
Conditional execution:
```
IF A > 10 THEN PRINT "BIG"
IF A > 10 THEN PRINT "BIG" ELSE PRINT "SMALL"
IF X = 0 THEN 100           : REM GOTO line 100 if true
IF A$ = "YES" THEN GOSUB 500
```

### GOTO
Unconditional jump to a line number:
```
GOTO 100
```

### GOSUB / RETURN
Call a subroutine at a line number; RETURN goes back:
```
10 GOSUB 1000
20 PRINT "BACK FROM SUBROUTINE"
30 END
1000 PRINT "IN SUBROUTINE"
1010 RETURN
```
Up to 64 nested GOSUB calls are supported.

### FOR / NEXT / STEP
Counted loop:
```
FOR I = 1 TO 10
  PRINT I
NEXT I

FOR X = 0 TO 1 STEP 0.1    : REM fractional step
  PRINT X
NEXT X

FOR I = 10 TO 1 STEP -1    : REM count down
  PRINT I
NEXT I
```
NEXT with no variable name closes the most recent FOR loop.
Up to 32 nested FOR loops are supported.

### ON / GOTO and ON / GOSUB
Branch to one of several line numbers based on a value:
```
ON N GOTO 100, 200, 300
ON N GOSUB 1000, 2000, 3000
```
If N=1, jump to the first target; N=2 to second; etc.
If N is out of range, execution continues on the next statement.

### DIM
Declare an array. Arrays are 0-based; DIM A(10) creates indices 0 through 10:
```
DIM A(100)        : REM numeric array, 101 elements (0-100)
DIM B$(50)        : REM string array (not yet implemented in all builds)
DIM X(10), Y(10)  : REM multiple arrays on one line
```

### DATA / READ / RESTORE
Embed data values in the program; read them sequentially:
```
10 DATA 1, 2, 3, "HELLO", 4.5
20 READ A, B, C, S$, D
30 PRINT A, B, C, S$, D
40 RESTORE             : REM reset READ pointer to beginning
50 READ A              : REM reads 1 again
```

### END
Stop execution and return to the READY prompt:
```
999 END
```

### STOP
Same as END, but prints BREAK:
```
STOP
```

### CLR
Clear all variables, arrays, and stacks (keep program):
```
CLR
```

### CLS
Clear the screen:
```
CLS
```

### SLEEP
Pause execution. 60 ticks = 1 second (authentic C64 timing):
```
SLEEP 60     : REM wait 1 second
SLEEP 30     : REM wait 0.5 seconds
SLEEP 180    : REM wait 3 seconds
```

### POKE
Accepted for compatibility but does nothing:
```
POKE 53280, 0
```

---

## Operators

### Arithmetic

| Operator | Meaning | Example |
|----------|---------|---------|
| `+` | Addition | `A + B` |
| `-` | Subtraction / Negation | `A - B` |
| `*` | Multiplication | `A * B` |
| `/` | Division | `A / B` |
| `^` | Exponentiation | `2 ^ 8` → 256 |

### Relational (return -1 for true, 0 for false)

| Operator | Meaning |
|----------|---------|
| `=` | Equal |
| `<>` | Not equal |
| `<` | Less than |
| `>` | Greater than |
| `<=` | Less than or equal |
| `>=` | Greater than or equal |

### Logical

| Operator | Meaning |
|----------|---------|
| `AND` | Bitwise AND |
| `OR` | Bitwise OR |
| `NOT` | Logical NOT |

### Precedence (highest to lowest)

1. Functions, parentheses
2. `^` (right-associative)
3. Unary `-`, `+`
4. `*`, `/`
5. `+`, `-`
6. `<`, `>`, `=`, `<>`, `<=`, `>=`
7. `NOT`
8. `AND`
9. `OR`

---

## Numeric Functions

| Function | Description | Example |
|----------|-------------|---------|
| `ABS(x)` | Absolute value | `ABS(-5)` → 5 |
| `INT(x)` | Floor (round down) | `INT(3.9)` → 3 |
| `SGN(x)` | Sign: -1, 0, or 1 | `SGN(-7)` → -1 |
| `SQR(x)` | Square root | `SQR(16)` → 4 |
| `EXP(x)` | e raised to x | `EXP(1)` → 2.71828... |
| `LOG(x)` | Natural logarithm | `LOG(1)` → 0 |
| `SIN(x)` | Sine (radians) | `SIN(3.14159)` → ~0 |
| `COS(x)` | Cosine (radians) | `COS(0)` → 1 |
| `TAN(x)` | Tangent (radians) | `TAN(0.785)` → ~1 |
| `ATN(x)` | Arctangent (radians) | `ATN(1)*4` → pi |
| `RND(x)` | Random number 0 to <1 | `RND(1)` |
| `PEEK(n)` | Read memory (stub, returns 0) | `PEEK(53280)` |

**RND notes:** The argument is ignored; the result is always a new random float
in [0, 1). To get a random integer 1–6: `INT(RND(1)*6)+1`

---

## String Functions

| Function | Description | Example |
|----------|-------------|---------|
| `LEN(s$)` | Length of string | `LEN("HELLO")` → 5 |
| `LEFT$(s$, n)` | First n characters | `LEFT$("HELLO",3)` → "HEL" |
| `RIGHT$(s$, n)` | Last n characters | `RIGHT$("HELLO",3)` → "LLO" |
| `MID$(s$, p, n)` | n chars starting at position p (1-based) | `MID$("HELLO",2,3)` → "ELL" |
| `MID$(s$, p)` | From position p to end | `MID$("HELLO",3)` → "LLO" |
| `CHR$(n)` | Character with ASCII code n | `CHR$(65)` → "A" |
| `ASC(s$)` | ASCII code of first character | `ASC("A")` → 65 |
| `STR$(n)` | Number to string | `STR$(42)` → " 42" |
| `VAL(s$)` | String to number | `VAL("3.14")` → 3.14 |
| `STRING$(n, c$)` | Repeat character n times | `STRING$(5,"*")` → "*****" |
| `STRING$(n, k)` | Repeat CHR$(k) n times | `STRING$(3,65)` → "AAA" |

**String concatenation** uses `+`:
```
A$ = "HELLO" + " " + "WORLD"
PRINT LEFT$(A$, 5) + "!"
```

---

## Print Formatting

### Semicolon `;`
- Between items: no space added, items run together
- At end of line: suppresses the newline (next PRINT continues on same line)

```
PRINT "A"; "B"; "C"    → ABC
PRINT 1; 2; 3          →  1  2  3
PRINT "NO";            → NO    (cursor stays on same line)
```

### Comma `,`
Advances to the next 14-column print zone:
```
PRINT "A", "B", "C"
→ A             B             C
  ^col 0        ^col 14       ^col 28
```

### TAB(n)
Move to column n (does nothing if already past that column):
```
PRINT TAB(20); "HELLO"
```

### SPC(n)
Print exactly n spaces regardless of current column:
```
PRINT "A"; SPC(10); "B"
```

---

## Arrays

Declare with DIM before use. Indices run from 0 to the declared size:

```
10 DIM SCORES(9)        : REM 10 elements: SCORES(0) to SCORES(9)
20 FOR I=0 TO 9
30   SCORES(I) = I*10
40 NEXT I
50 FOR I=0 TO 9
60   PRINT SCORES(I);" ";
70 NEXT I
```

---

## DATA, READ, RESTORE

DATA lines are collected before the program runs. READ pulls values from
the data pool in order. RESTORE resets the pointer to the beginning:

```
10 FOR I=1 TO 5
20   READ N
30   PRINT N
40 NEXT I
50 RESTORE
60 READ A : PRINT "FIRST AGAIN:";A
70 END
80 DATA 10, 20, 30, 40, 50
```

Mixed types are allowed:
```
100 DATA "ALICE", 95, "BOB", 82
110 READ N$, S
120 PRINT N$;" SCORED ";S
```

---

## Subroutines

GOSUB jumps to a line and saves the return address. RETURN goes back.
Subroutines can be nested up to 64 levels deep:

```
10 GOSUB 1000
20 GOSUB 2000
30 END

1000 REM -- DRAW LINE --
1010 PRINT STRING$(40,"-")
1020 RETURN

2000 REM -- GREET --
2010 PRINT "HELLO FROM SUBROUTINE"
2020 RETURN
```

---

## Common Patterns

### Degrees to Radians

```
10 PI = ATN(1)*4
20 DEG = 45
30 RAD = DEG * PI / 180
40 PRINT SIN(RAD)
```

### Random Integer in a Range

```
10 REM Random integer from LO to HI inclusive
20 LO=1 : HI=6
30 N = INT(RND(1) * (HI-LO+1)) + LO
40 PRINT N
```

### String Padding / Alignment

```
10 FOR I=1 TO 10
20   PRINT TAB(4-LEN(STR$(I))); I; TAB(8); I*I
30 NEXT I
```

### Main Loop with Menu

```
10 PRINT "1. PLAY"
20 PRINT "2. SCORES"
30 PRINT "3. QUIT"
40 INPUT "CHOICE";C
50 ON C GOTO 100, 200, 300
60 PRINT "INVALID" : GOTO 10
100 PRINT "PLAYING..." : GOTO 10
200 PRINT "SCORES..." : GOTO 10
300 PRINT "BYE!" : END
```

---

## Error Messages

| Message | Cause |
|---------|-------|
| `?SYNTAX ERROR IN n` | Unrecognised statement on line n |
| `?UNDEF'D STATEMENT IN n` | GOTO/GOSUB target line does not exist |
| `?NEXT WITHOUT FOR` | NEXT with no matching FOR |
| `?RETURN WITHOUT GOSUB` | RETURN with no matching GOSUB |
| `?OUT OF DATA ERROR` | READ past the end of all DATA |
| `?LINE NOT FOUND` | RUN start_line doesn't exist |
| `?NO PROGRAM` | RUN with no lines in memory |
| `BREAK` | Ctrl+C pressed during execution |
