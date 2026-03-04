# BSDBASIC — Quick Reference Card

## Shell Commands
```
RUN          run program        LIST         list program
NEW          clear all          CLR          clear vars only
LOAD name    load sample/.bas   SAVE name    save to .bas
DIR          show .bas files    HELP         command list
EXIT / BYE   quit
```

## Statement Quick Reference
```
PRINT expr [;expr] [;|,]    output
? expr                       PRINT shorthand
INPUT ["prompt";] var        read input
LET var = expr               assign (LET optional)
FOR v=n TO n [STEP n]        loop start
NEXT [v]                     loop end
GOTO n                       jump to line n
GOSUB n                      call subroutine at line n
RETURN                       return from subroutine
IF expr THEN stmt [ELSE stmt]  conditional
ON expr GOTO n,n,n,...       computed jump
ON expr GOSUB n,n,n,...      computed call
DIM var(size)                declare array (0..size)
DATA v,v,"s",...             embed data values
READ var [,var]              read next data value
RESTORE                      reset data pointer
REM text                     comment
END / STOP                   halt program
SLEEP ticks                  pause (60 ticks = 1 sec)
CLS                          clear screen
POKE addr,val                stub (no-op)
```

## Operators (high to low precedence)
```
^              exponentiation
- (unary)      negation
* /            multiply, divide
+ -            add, subtract
= <> < > <= >= relational (return -1 or 0)
NOT            bitwise NOT
AND            bitwise AND
OR             bitwise OR
```

## Math Functions
```
SIN(x)   COS(x)   TAN(x)   ATN(x)
EXP(x)   LOG(x)   SQR(x)   ABS(x)
INT(x)   SGN(x)   RND(x)
```

## String Functions
```
LEN(s$)              length
LEFT$(s$,n)          first n chars
RIGHT$(s$,n)         last n chars
MID$(s$,p[,n])       substring from p (1-based)
CHR$(n)              char from ASCII code
ASC(s$)              ASCII code of first char
STR$(n)              number to string
VAL(s$)              string to number
STRING$(n,c$)        n copies of char c$
s$ + t$              concatenation
```

## PRINT Formatting
```
;   no separator / suppress newline at end
,   advance to next 14-column zone
TAB(col)    move to absolute column
SPC(n)      print n spaces
```

## Variable Naming
```
Numeric:  A  B  X1  COUNTER         (letters + digits)
String:   A$ NAME$ RESULT$          (end with $)
Array:    DIM A(10)  → A(0)..A(10)  (11 elements)
```

## Common Patterns
```basic
REM Degrees to radians
RAD = DEG * 3.14159265 / 180

REM Random integer 1-6
PRINT INT(RND(1)*6)+1

REM Count down
FOR I=10 TO 1 STEP -1 : PRINT I : NEXT I

REM Subroutine
GOSUB 1000 : END
1000 PRINT "SUB" : RETURN

REM Data table
READ N$,V : DATA "PI",3.14159,"E",2.71828

REM String repeat
PRINT STRING$(40,"-")
```

## Error Messages
```
?SYNTAX ERROR IN n          bad statement on line n
?UNDEF'D STATEMENT IN n     GOTO/GOSUB target missing
?RETURN WITHOUT GOSUB       stray RETURN
?NEXT WITHOUT FOR           stray NEXT
?OUT OF DATA ERROR          READ past end of DATA
?NO PROGRAM                 RUN with empty program
BREAK                       stopped by END/STOP/Ctrl-C
```

## File Format (.bas)
Plain text, one line per record:
```
10 PRINT "HELLO"
20 END
```
