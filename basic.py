#!/usr/bin/env python3
"""
bsdbasic.py — Microsoft CBM BASIC V2 interpreter for the terminal
Compatible with: Python 3.6+, Termux (Android), Linux, macOS

Usage:
    python3 basic.py          # interactive REPL
    python3 basic.py prog.bas # run a .bas file

Supported: FOR/NEXT, GOSUB/RETURN, GOTO, IF/THEN/ELSE, PRINT, INPUT,
           LET, DIM, DATA/READ/RESTORE, ON GOTO/GOSUB, SLEEP,
           TAB(), SPC(), all math functions, all string functions,
           AND, OR, NOT, string variables, arrays
"""

import sys
import os
import math
import time
import random

# ─── ANSI colours (auto-disabled if not a tty) ───────────────────
_IS_TTY = sys.stdout.isatty()

def _c(code): return f"\033[{code}m" if _IS_TTY else ""

RESET  = _c("0")
BOLD   = _c("1")
BLUE   = _c("34")
CYAN   = _c("36")
YELLOW = _c("33")
WHITE  = _c("97")
DIM    = _c("2")
RED    = _c("31")

# C64-ish colour scheme
C_PROMPT  = CYAN + BOLD     # ready prompt / line numbers
C_OUTPUT  = WHITE           # program output
C_ERROR   = RED + BOLD      # error messages
C_META    = DIM + CYAN      # system messages
C_INPUT   = YELLOW          # user input echo / INPUT prompt
C_RESET   = RESET

# ─── readline support (graceful fallback) ────────────────────────
try:
    import readline
    _HISTORY_FILE = os.path.expanduser("~/.bsdbasic_history")
    try:    readline.read_history_file(_HISTORY_FILE)
    except: pass
    import atexit
    atexit.register(lambda: readline.write_history_file(_HISTORY_FILE))
    _READLINE = True
except ImportError:
    _READLINE = False


# ════════════════════════════════════════════════════════════════════
#  Tokeniser / parser helpers
# ════════════════════════════════════════════════════════════════════

class ParseState:
    __slots__ = ("src", "pos", "line_num")
    def __init__(self, src, line_num=0):
        self.src      = src.rstrip()
        self.pos      = 0
        self.line_num = line_num

    def rest(self):   return self.src[self.pos:]
    def peek(self):   return self.src[self.pos] if self.pos < len(self.src) else ""
    def at_end(self): return self.pos >= len(self.src)

    def skip_ws(self):
        while self.pos < len(self.src) and self.src[self.pos] in (" ", "\t"):
            self.pos += 1

    def match_ch(self, c):
        self.skip_ws()
        if self.peek() == c:
            self.pos += 1
            self.skip_ws()
            return True
        return False

    def expect_ch(self, c):
        self.skip_ws()
        if self.peek() == c:
            self.pos += 1
            self.skip_ws()

    def match_kw(self, kw):
        """Match keyword at current pos; word-boundary safe."""
        self.skip_ws()
        upper = self.src.upper()
        u     = kw.upper()
        if not upper[self.pos:].startswith(u):
            return False
        after = self.pos + len(u)
        if after < len(self.src) and (self.src[after].isalnum() or self.src[after] in ("_", "$")):
            return False
        self.pos = after
        self.skip_ws()
        return True

    def match_kw_lp(self, kw):
        """Match keyword immediately followed by '(' (optional spaces)."""
        self.skip_ws()
        upper = self.src.upper()
        u     = kw.upper()
        if not upper[self.pos:].startswith(u):
            return False
        j = self.pos + len(u)
        while j < len(self.src) and self.src[j] == " ":
            j += 1
        if j >= len(self.src) or self.src[j] != "(":
            return False
        self.pos = j + 1   # consume keyword + spaces + (
        self.skip_ws()
        return True

    def read_ident(self):
        self.skip_ws()
        if self.at_end() or not self.src[self.pos].isalpha():
            return None
        start = self.pos
        while self.pos < len(self.src) and (self.src[self.pos].isalnum() or self.src[self.pos] == "_"):
            self.pos += 1
        if self.pos < len(self.src) and self.src[self.pos] == "$":
            self.pos += 1
        name = self.src[start:self.pos].upper()
        self.skip_ws()
        return name

    def read_str_lit(self):
        """Read a quoted string; pos must be on the opening quote."""
        self.pos += 1   # skip "
        buf = []
        while self.pos < len(self.src) and self.src[self.pos] != '"':
            buf.append(self.src[self.pos])
            self.pos += 1
        if self.pos < len(self.src):
            self.pos += 1   # skip closing "
        return "".join(buf)

    def clone(self):
        p2 = ParseState(self.src, self.line_num)
        p2.pos = self.pos
        return p2


# ════════════════════════════════════════════════════════════════════
#  BASIC interpreter
# ════════════════════════════════════════════════════════════════════

class BasicError(Exception):
    pass

class GotoSignal(Exception):
    def __init__(self, line): self.line = line

class GosubSignal(Exception):
    def __init__(self, line): self.line = line

class ReturnSignal(Exception): pass
class NextSignal(Exception):
    def __init__(self, var): self.var = var

class StopSignal(Exception): pass


class Interpreter:
    MAX_FOR_DEPTH   = 32
    MAX_GOSUB_DEPTH = 64

    def __init__(self):
        self.lines     = {}      # int -> str
        self.num_vars  = {}      # str -> float
        self.str_vars  = {}      # str -> str
        self.arrays    = {}      # str -> list
        self.for_stack = []      # list of dicts
        self.gosub_stack = []    # list of (line_idx, rest_pos) — we store return line indices
        self.data_items  = []    # list of (is_str, val)
        self.data_ptr    = 0
        self.print_col   = 0
        self.running     = False
        self.stopped     = False
        self._sorted_keys = None  # cached sorted line numbers

    # ── Program management ────────────────────────────────────────
    def add_line(self, num, text):
        t = text.strip()
        if t:
            self.lines[num] = t
        elif num in self.lines:
            del self.lines[num]
        self._sorted_keys = None

    def sorted_keys(self):
        if self._sorted_keys is None:
            self._sorted_keys = sorted(self.lines)
        return self._sorted_keys

    def list_program(self):
        keys = self.sorted_keys()
        if not keys:
            return "(NO PROGRAM)"
        return "\n".join(f"{C_PROMPT}{n}{C_RESET} {self.lines[n]}" for n in keys)

    def new_program(self):
        self.lines.clear()
        self._sorted_keys = None
        self.clr_vars()

    def clr_vars(self):
        self.num_vars.clear()
        self.str_vars.clear()
        self.arrays.clear()
        self.for_stack.clear()
        self.gosub_stack.clear()
        self.data_items.clear()
        self.data_ptr  = 0
        self.print_col = 0

    # ── Output ────────────────────────────────────────────────────
    def raw_print(self, s):
        sys.stdout.write(C_OUTPUT + s + C_RESET)
        sys.stdout.flush()
        for c in s:
            if c == "\n":
                self.print_col = 0
            else:
                self.print_col += 1

    def println(self, s=""):
        self.raw_print(s + "\n")

    # ── DATA collection ───────────────────────────────────────────
    def collect_data(self):
        self.data_items = []
        for n in self.sorted_keys():
            text = self.lines[n]
            i    = 0
            while i < len(text):
                while i < len(text) and text[i] == " ":
                    i += 1
                up = text[i:].upper()
                if up.startswith("DATA") and (len(up) == 4 or not up[4].isalnum()):
                    i += 4
                    while True:
                        while i < len(text) and text[i] == " ":
                            i += 1
                        if i < len(text) and text[i] == '"':
                            i += 1
                            s = []
                            while i < len(text) and text[i] != '"':
                                s.append(text[i]); i += 1
                            if i < len(text): i += 1
                            self.data_items.append((True, "".join(s)))
                        else:
                            tok = []
                            while i < len(text) and text[i] not in (",", ":"):
                                tok.append(text[i]); i += 1
                            raw = "".join(tok).strip()
                            try:    self.data_items.append((False, float(raw)))
                            except: self.data_items.append((False, 0.0))
                        while i < len(text) and text[i] == " ":
                            i += 1
                        if i < len(text) and text[i] == ",":
                            i += 1; continue
                        break
                elif up.upper().startswith("REM"):
                    break
                # skip to next colon
                while i < len(text) and text[i] != ":":
                    i += 1
                while i < len(text) and text[i] == ":":
                    i += 1

    # ── Main run loop ─────────────────────────────────────────────
    def run(self, start_line=None):
        self.clr_vars()
        self.collect_data()
        self.running = True
        self.stopped = False

        keys = self.sorted_keys()
        if not keys:
            self.println("?NO PROGRAM")
            self.running = False
            return

        if start_line is not None:
            li = next((i for i, k in enumerate(keys) if k >= start_line), -1)
            if li < 0:
                self.println("?LINE NOT FOUND")
                self.running = False
                return
        else:
            li = 0

        try:
            while not self.stopped and 0 <= li < len(keys):
                line_num = keys[li]
                text     = self.lines[line_num]
                jumped   = False
                p        = ParseState(text, line_num)

                while not p.at_end() and not self.stopped:
                    p.skip_ws()
                    if p.at_end(): break

                    try:
                        result = self._exec_stmt(p)
                    except GotoSignal as g:
                        li = next((i for i, k in enumerate(keys) if k >= g.line), -1)
                        if li < 0:
                            raise BasicError(f"?UNDEF'D STATEMENT IN {line_num}")
                        jumped = True; break
                    except GosubSignal as g:
                        self.gosub_stack.append(li)
                        li = next((i for i, k in enumerate(keys) if k >= g.line), -1)
                        if li < 0:
                            raise BasicError(f"?UNDEF'D STATEMENT IN {line_num}")
                        jumped = True; break
                    except ReturnSignal:
                        if not self.gosub_stack:
                            raise BasicError("?RETURN WITHOUT GOSUB")
                        li = self.gosub_stack.pop() + 1
                        jumped = True; break
                    except NextSignal as ns:
                        # Find matching FOR frame
                        nv = ns.var.upper() if ns.var else ""
                        fi = len(self.for_stack) - 1
                        if nv:
                            while fi >= 0 and self.for_stack[fi]["var"] != nv:
                                fi -= 1
                        if fi < 0:
                            raise BasicError("?NEXT WITHOUT FOR")
                        frame = self.for_stack[fi]
                        val   = self.num_vars.get(frame["var"], 0.0) + frame["step"]
                        self.num_vars[frame["var"]] = val
                        done  = (val > frame["to"]) if frame["step"] >= 0 else (val < frame["to"])
                        if not done:
                            # jump to line after the FOR line
                            for_li = next((i for i, k in enumerate(keys) if k >= frame["line_num"]), 0)
                            li = for_li + 1
                            jumped = True
                        else:
                            self.for_stack.pop(fi)
                        break

                    p.skip_ws()
                    if p.peek() == ":":
                        p.pos += 1

                if not jumped and not self.stopped:
                    li += 1

        except StopSignal:
            pass
        except BasicError as e:
            sys.stdout.write(f"\n{C_ERROR}{e}{C_RESET}\n")
        except KeyboardInterrupt:
            sys.stdout.write(f"\n{C_ERROR}BREAK{C_RESET}\n")

        self.running = False

    # ── Statement dispatcher ──────────────────────────────────────
    def _exec_stmt(self, p):
        p.skip_ws()
        if p.at_end() or p.peek() == ":":
            return

        # REM
        if p.match_kw("REM"):
            p.pos = len(p.src); return

        # PRINT / ?
        if p.match_kw("PRINT") or p.peek() == "?":
            if p.peek() == "?": p.pos += 1
            self._do_print(p); return

        # INPUT
        if p.match_kw("INPUT"):
            self._do_input(p); return

        # Try assignment (with optional LET)
        saved = p.pos
        p.match_kw("LET")
        saved2 = p.pos
        name = p.read_ident()
        if name:
            p.skip_ws()
            if p.peek() in ("=", "("):
                self._do_assign(p, name); return
        p.pos = saved

        # GOTO
        if p.match_kw("GOTO"):
            raise GotoSignal(int(self._parse_expr(p)))

        # GOSUB
        if p.match_kw("GOSUB"):
            raise GosubSignal(int(self._parse_expr(p)))

        # RETURN
        if p.match_kw("RETURN"):
            raise ReturnSignal()

        # FOR
        if p.match_kw("FOR"):
            var  = p.read_ident()
            p.expect_ch("=")
            frm  = self._parse_expr(p)
            p.match_kw("TO")
            to   = self._parse_expr(p)
            step = 1.0
            if p.match_kw("STEP"):
                step = self._parse_expr(p)
            self.num_vars[var] = frm
            if len(self.for_stack) >= self.MAX_FOR_DEPTH:
                raise BasicError("?OUT OF MEMORY ERROR (FOR STACK)")
            self.for_stack.append({"var": var, "to": to, "step": step, "line_num": p.line_num})
            return

        # NEXT
        if p.match_kw("NEXT"):
            var = p.read_ident() or ""
            raise NextSignal(var)

        # IF
        if p.match_kw("IF"):
            cond = self._parse_expr(p)
            p.match_kw("THEN")
            p.skip_ws()
            if cond != 0:
                if p.peek().isdigit():
                    raise GotoSignal(int(self._parse_expr(p)))
                self._exec_stmt(p)
            else:
                up = p.src.upper()
                ei = up.find("ELSE", p.pos)
                if ei >= 0:
                    p.pos = ei + 4
                    p.skip_ws()
                    if p.peek().isdigit():
                        raise GotoSignal(int(self._parse_expr(p)))
                    self._exec_stmt(p)
                else:
                    p.pos = len(p.src)
            return

        # ON x GOTO/GOSUB
        if p.match_kw("ON"):
            idx = int(self._parse_expr(p))
            is_gosub = p.match_kw("GOSUB")
            if not is_gosub: p.match_kw("GOTO")
            targets = []
            while p.peek().isdigit():
                targets.append(int(self._parse_expr(p)))
                p.skip_ws()
                if p.peek() == ",": p.pos += 1; p.skip_ws()
                else: break
            if 1 <= idx <= len(targets):
                if is_gosub: raise GosubSignal(targets[idx - 1])
                else:        raise GotoSignal(targets[idx - 1])
            return

        # DIM
        if p.match_kw("DIM"):
            while True:
                name = p.read_ident()
                p.expect_ch("(")
                sz = int(self._parse_expr(p)) + 1  # CBM: DIM A(10) → 0..10 = 11 elements
                p.expect_ch(")")
                self.arrays[name] = [0.0] * sz
                p.skip_ws()
                if p.peek() == ",": p.pos += 1; p.skip_ws()
                else: break
            return

        # DATA (skip — collected before run)
        if p.match_kw("DATA"):
            p.pos = len(p.src); return

        # READ
        if p.match_kw("READ"):
            while True:
                name = p.read_ident()
                if self.data_ptr >= len(self.data_items):
                    raise BasicError("?OUT OF DATA ERROR")
                is_str, val = self.data_items[self.data_ptr]; self.data_ptr += 1
                if name.endswith("$"):
                    self.str_vars[name] = str(val) if not is_str else val
                else:
                    self.num_vars[name] = float(val) if not is_str else (float(val) if val.replace(".","").replace("-","").isdigit() else 0.0)
                p.skip_ws()
                if p.peek() == ",": p.pos += 1; p.skip_ws()
                else: break
            return

        # RESTORE
        if p.match_kw("RESTORE"):
            self.data_ptr = 0; return

        # END / STOP
        if p.match_kw("END") or p.match_kw("STOP"):
            raise StopSignal()

        # SLEEP (ticks; 60 ticks = 1 second)
        if p.match_kw("SLEEP"):
            ticks = self._parse_expr(p)
            try:
                time.sleep(ticks / 60.0)
            except KeyboardInterrupt:
                raise
            return

        # CLS
        if p.match_kw("CLS"):
            sys.stdout.write("\033[2J\033[H"); sys.stdout.flush()
            self.print_col = 0; return

        # POKE (stub)
        if p.match_kw("POKE"):
            self._parse_expr(p); p.expect_ch(","); self._parse_expr(p); return

        raise BasicError(f"?SYNTAX ERROR IN {p.line_num}: {p.rest()[:20]!r}")

    # ── Assignment ────────────────────────────────────────────────
    def _do_assign(self, p, name):
        p.skip_ws()
        if p.peek() == "(":
            p.pos += 1; p.skip_ws()
            idx = int(self._parse_expr(p))
            p.expect_ch(")"); p.expect_ch("=")
            arr = self.arrays.setdefault(name, [0.0] * (idx + 1))
            if idx >= len(arr): arr.extend([0.0] * (idx - len(arr) + 1))
            if name.endswith("$"): arr[idx] = self._parse_str_expr(p)
            else:                   arr[idx] = self._parse_expr(p)
            return
        p.expect_ch("=")
        if name.endswith("$"):
            self.str_vars[name] = self._parse_str_expr(p)
        else:
            self.num_vars[name] = self._parse_expr(p)

    # ── PRINT ─────────────────────────────────────────────────────
    def _do_print(self, p):
        newline = True
        while not p.at_end() and p.peek() != ":":
            p.skip_ws()
            if p.at_end() or p.peek() == ":": break

            if p.match_kw_lp("TAB"):
                col = int(self._parse_expr(p)); p.expect_ch(")")
                while self.print_col < col: self.raw_print(" ")
            elif p.match_kw_lp("SPC"):
                n = int(self._parse_expr(p)); p.expect_ch(")")
                self.raw_print(" " * n)
            elif self._looks_like_str(p):
                self.raw_print(self._parse_str_expr(p))
            else:
                v = self._parse_expr(p)
                # C64 formatting: integers show without decimal
                if v == int(v):
                    self.raw_print(str(int(v)) + " ")
                else:
                    s = f"{v:.9g}"
                    self.raw_print(s + " ")

            p.skip_ws()
            if p.peek() == ";":
                p.pos += 1; p.skip_ws()
                # trailing semicolon → suppress newline
                if p.at_end() or p.peek() == ":":
                    newline = False; break
                # mid-line → continue printing without gap
            elif p.peek() == ",":
                # advance to next 14-column print zone
                zone = (self.print_col // 14 + 1) * 14
                while self.print_col < zone: self.raw_print(" ")
                p.pos += 1; p.skip_ws()
                if p.at_end() or p.peek() == ":":
                    newline = False; break
            else:
                break

        if newline:
            self.raw_print("\n")

    def _looks_like_str(self, p):
        rest = p.rest().upper()
        if rest.startswith('"'): return True
        for fn in ("CHR$", "STR$", "LEFT$", "RIGHT$", "MID$", "STRING$"):
            if rest.startswith(fn): return True
        # identifier ending in $
        i = 0
        while i < len(rest) and (rest[i].isalpha() or (i > 0 and rest[i].isalnum())):
            i += 1
        return i > 0 and i < len(rest) and rest[i] == "$"

    # ── INPUT ─────────────────────────────────────────────────────
    def _do_input(self, p):
        prompt = "? "
        p.skip_ws()
        if p.peek() == '"':
            prompt = p.read_str_lit()
            if p.peek() in (";", ","): p.pos += 1
        sys.stdout.write(C_INPUT + prompt + C_RESET)
        sys.stdout.flush()
        try:
            answer = input()
        except EOFError:
            answer = ""
        self.print_col = 0
        parts = answer.split(",")
        pi = 0
        while not p.at_end() and p.src[p.pos].isalpha():
            name = p.read_ident()
            val  = parts[pi].strip() if pi < len(parts) else ""
            pi  += 1
            if name.endswith("$"):
                self.str_vars[name] = val
            else:
                try:    self.num_vars[name] = float(val)
                except: self.num_vars[name] = 0.0
            p.skip_ws()
            if p.peek() == ",": p.pos += 1; p.skip_ws()
            else: break

    # ════════════════════════════════════════════════════════════════
    #  Expression parser  (recursive descent)
    # ════════════════════════════════════════════════════════════════

    def _parse_expr(self, p):   return self._parse_or(p)

    def _parse_or(self, p):
        v = self._parse_and(p)
        while p.match_kw("OR"):
            v = int(v) | int(self._parse_and(p))
        return float(v)

    def _parse_and(self, p):
        v = self._parse_not(p)
        while p.match_kw("AND"):
            v = int(v) & int(self._parse_not(p))
        return float(v)

    def _parse_not(self, p):
        if p.match_kw("NOT"):
            return -1.0 if self._parse_not(p) == 0 else 0.0
        return self._parse_rel(p)

    def _parse_rel(self, p):
        left = self._parse_add(p)
        p.skip_ws()
        s = p.src
        i = p.pos
        if s[i:i+2] == "<>": p.pos+=2; return -1.0 if left != self._parse_add(p) else 0.0
        if s[i:i+2] == "<=": p.pos+=2; return -1.0 if left <= self._parse_add(p) else 0.0
        if s[i:i+2] == ">=": p.pos+=2; return -1.0 if left >= self._parse_add(p) else 0.0
        if s[i:i+1] == "<":  p.pos+=1; return -1.0 if left <  self._parse_add(p) else 0.0
        if s[i:i+1] == ">":  p.pos+=1; return -1.0 if left >  self._parse_add(p) else 0.0
        if s[i:i+1] == "=":  p.pos+=1; return -1.0 if left == self._parse_add(p) else 0.0
        return left

    def _parse_add(self, p):
        v = self._parse_mul(p)
        while True:
            p.skip_ws()
            if   p.peek() == "+": p.pos += 1; v += self._parse_mul(p)
            elif p.peek() == "-": p.pos += 1; v -= self._parse_mul(p)
            else: break
        return v

    def _parse_mul(self, p):
        v = self._parse_unary(p)
        while True:
            p.skip_ws()
            if p.peek() == "*": p.pos += 1; v *= self._parse_unary(p)
            elif p.peek() == "/":
                p.pos += 1
                d = self._parse_unary(p)
                v = v / d if d != 0 else 0.0
            else: break
        return v

    def _parse_unary(self, p):
        p.skip_ws()
        if p.peek() == "-": p.pos += 1; return -self._parse_pow(p)
        if p.peek() == "+": p.pos += 1; return  self._parse_pow(p)
        return self._parse_pow(p)

    def _parse_pow(self, p):
        b = self._parse_primary(p)
        p.skip_ws()
        if p.peek() == "^":
            p.pos += 1
            return float(b ** self._parse_unary(p))
        return b

    # ── Math functions table ──────────────────────────────────────
    _MATH_FNS = {
        "SIN": math.sin, "COS": math.cos, "TAN": math.tan, "ATN": math.atan,
        "EXP": math.exp, "LOG": math.log, "SQR": math.sqrt, "ABS": abs,
        "INT": math.floor,
    }

    def _parse_primary(self, p):
        p.skip_ws()

        # Parenthesised expression
        if p.peek() == "(":
            p.pos += 1; p.skip_ws()
            v = self._parse_expr(p)
            p.expect_ch(")")
            return v

        # Numeric literal
        rest = p.rest()
        if rest and (rest[0].isdigit() or (rest[0] == "." and len(rest) > 1 and rest[1].isdigit())):
            j = 0
            while j < len(rest) and (rest[j].isdigit() or rest[j] == "."):
                j += 1
            if j < len(rest) and rest[j] in ("e", "E"):
                j += 1
                if j < len(rest) and rest[j] in ("+", "-"): j += 1
                while j < len(rest) and rest[j].isdigit(): j += 1
            p.pos += j
            p.skip_ws()
            return float(rest[:j])

        # Math functions
        for name, fn in self._MATH_FNS.items():
            if p.match_kw_lp(name):
                v = self._parse_expr(p); p.expect_ch(")")
                return float(fn(v))

        # SGN
        if p.match_kw_lp("SGN"):
            v = self._parse_expr(p); p.expect_ch(")")
            return 1.0 if v > 0 else (-1.0 if v < 0 else 0.0)

        # LEN (takes string arg)
        if p.match_kw_lp("LEN"):
            s = self._parse_str_expr(p); p.expect_ch(")")
            return float(len(s))

        # ASC
        if p.match_kw_lp("ASC"):
            s = self._parse_str_expr(p); p.expect_ch(")")
            return float(ord(s[0])) if s else 0.0

        # VAL
        if p.match_kw_lp("VAL"):
            s = self._parse_str_expr(p); p.expect_ch(")")
            try:    return float(s.strip())
            except: return 0.0

        # RND(n)  — ignore argument; always return [0,1)
        if p.match_kw_lp("RND"):
            self._parse_expr(p); p.expect_ch(")")
            return random.random()

        # PEEK (stub)
        if p.match_kw_lp("PEEK"):
            self._parse_expr(p); p.expect_ch(")")
            return 0.0

        # TAB / SPC in expression context
        if p.match_kw_lp("TAB") or p.match_kw_lp("SPC"):
            v = self._parse_expr(p); p.expect_ch(")")
            return v

        # Identifier: variable or array
        name = p.read_ident()
        if name:
            if name.endswith("$"):
                return 0.0   # string var in numeric context
            p.skip_ws()
            if p.peek() == "(":
                p.pos += 1; p.skip_ws()
                idx = int(self._parse_expr(p))
                p.expect_ch(")")
                arr = self.arrays.get(name, [])
                return float(arr[idx]) if 0 <= idx < len(arr) else 0.0
            return self.num_vars.get(name, 0.0)

        # Unknown: skip character
        p.pos += 1
        return 0.0

    # ── String expressions ────────────────────────────────────────
    def _parse_str_expr(self, p):
        p.skip_ws()
        result = self._parse_str_primary(p)
        while p.peek() == "+":
            p.pos += 1
            result += self._parse_str_primary(p)
        return result

    def _parse_str_primary(self, p):
        p.skip_ws()

        # String literal
        if p.peek() == '"':
            return p.read_str_lit()

        # CHR$(n)
        if p.match_kw_lp("CHR$"):
            c = int(self._parse_expr(p)); p.expect_ch(")")
            return chr(c) if 0 <= c <= 127 else ""

        # STR$(n)
        if p.match_kw_lp("STR$"):
            v = self._parse_expr(p); p.expect_ch(")")
            if v == int(v): return " " + str(int(v))
            return " " + f"{v:.9g}"

        # LEFT$(s, n)
        if p.match_kw_lp("LEFT$"):
            s = self._parse_str_expr(p); p.expect_ch(",")
            n = int(self._parse_expr(p)); p.expect_ch(")")
            return s[:max(0, n)]

        # RIGHT$(s, n)
        if p.match_kw_lp("RIGHT$"):
            s = self._parse_str_expr(p); p.expect_ch(",")
            n = int(self._parse_expr(p)); p.expect_ch(")")
            return s[max(0, len(s) - n):]

        # MID$(s, pos [, len])
        if p.match_kw_lp("MID$"):
            s   = self._parse_str_expr(p); p.expect_ch(",")
            pos = int(self._parse_expr(p)) - 1   # 1-based
            length = len(s)
            if p.peek() == ",":
                p.pos += 1
                length = int(self._parse_expr(p))
            p.expect_ch(")")
            pos = max(0, pos)
            return s[pos:pos + length]

        # STRING$(n, char)
        if p.match_kw_lp("STRING$"):
            n = int(self._parse_expr(p)); p.expect_ch(",")
            if p.peek() == '"':
                fill = p.read_str_lit()
                fill = fill[0] if fill else " "
            else:
                fill = chr(int(self._parse_expr(p)))
            p.expect_ch(")")
            return fill * max(0, n)

        # String variable
        name = p.read_ident()
        if name and name.endswith("$"):
            return self.str_vars.get(name, "")

        return ""


# ════════════════════════════════════════════════════════════════════
#  Interactive REPL / shell
# ════════════════════════════════════════════════════════════════════

BOOT_MSG = f"""\
{C_PROMPT}
    ****  CBM BASIC V2  ****

 64K RAM SYSTEM  38911 BASIC BYTES FREE

READY.
{C_RESET}"""

HELP_TEXT = f"""\
{C_META}──────────────────────────────────────────────
BSDBASIC — Commands
──────────────────────────────────────────────
  RUN         Run the current program
  LIST        List the program
  NEW         Clear the program and variables
  CLR         Clear variables only
  LOAD "name" Load a built-in sample program
  SAVE "name" Save program to a .bas file
  DIR         Show .bas files in current folder
  HELP        This message
  EXIT / BYE  Quit the interpreter

Enter lines like:  10 PRINT "HELLO"
Then type RUN.
──────────────────────────────────────────────{C_RESET}"""

SAMPLES = {
    "HELLO": """\
10 PRINT "HELLO, WORLD!"
20 PRINT "CBM BASIC V2 - PYTHON EDITION"
30 FOR I=1 TO 5
40 PRINT "ITERATION ";I
50 NEXT I
60 END""",

    "SINE": """\
10 REM ASCII SINE WAVE
20 FOR A=0 TO 630 STEP 5
30 PRINT TAB(39+38*SIN(A/100));"*"
40 NEXT A
50 PRINT "DONE!"
60 END""",

    "FIB": """\
10 PRINT "FIBONACCI SEQUENCE:"
20 A=0 : B=1
30 FOR I=1 TO 25
40 PRINT A;" ";
50 C=A+B : A=B : B=C
60 NEXT I
70 PRINT
80 END""",

    "COUNTDOWN": """\
10 PRINT "*** LAUNCH COUNTDOWN ***"
20 PRINT
30 FOR I=10 TO 1 STEP -1
40 PRINT I;"..."
50 SLEEP 30
60 NEXT I
70 PRINT "*** LIFTOFF! ***"
80 END""",

    "PRIMES": """\
10 PRINT "PRIME NUMBERS UP TO 200:"
20 DIM P(201)
30 FOR I=2 TO 200
40 P(I)=1
50 NEXT I
60 FOR I=2 TO 14
70 IF P(I)=0 THEN GOTO 110
80 FOR J=I*2 TO 200 STEP I
90 P(J)=0
100 NEXT J
110 NEXT I
120 FOR I=2 TO 200
130 IF P(I)=1 THEN PRINT I;" ";
140 NEXT I
150 PRINT
160 END""",

    "GUESS": """\
10 PRINT "*** GUESS MY NUMBER ***"
20 PRINT
30 N=INT(RND(1)*100)+1
40 G=0
50 PRINT "I AM THINKING OF A NUMBER 1-100"
60 INPUT "YOUR GUESS";A
70 G=G+1
80 IF A<N THEN PRINT "TOO LOW!" : GOTO 60
90 IF A>N THEN PRINT "TOO HIGH!" : GOTO 60
100 PRINT "CORRECT IN ";G;" GUESSES!"
110 END""",

    "STARS": """\
10 FOR I=1 TO 9 STEP 2
20 PRINT TAB((20-I)/2);STRING$(I,"*")
30 NEXT I
40 FOR I=7 TO 1 STEP -2
50 PRINT TAB((20-I)/2);STRING$(I,"*")
60 NEXT I
70 END""",

    "TIMES": """\
10 PRINT "MULTIPLICATION TABLE"
20 PRINT "--------------------"
30 FOR I=1 TO 10
40 FOR J=1 TO 10
50 PRINT TAB((J-1)*5);I*J;
60 NEXT J
70 PRINT
80 NEXT I
90 END""",
}

def load_sample(interp, name):
    key = name.upper().strip('"').strip("'")
    if key not in SAMPLES:
        # fuzzy: prefix match
        matches = [k for k in SAMPLES if k.startswith(key)]
        if len(matches) == 1:
            key = matches[0]
        else:
            print(f"{C_ERROR}?FILE NOT FOUND: {name}{C_RESET}")
            avail = "  " + "  ".join(SAMPLES.keys())
            print(f"{C_META}AVAILABLE:{C_RESET}\n{avail}")
            return False
    interp.new_program()
    for line in SAMPLES[key].splitlines():
        m_ln = line.strip().split(None, 1)
        if m_ln and m_ln[0].isdigit():
            interp.add_line(int(m_ln[0]), m_ln[1] if len(m_ln) > 1 else "")
    print(f"{C_META}LOADED: {key}{C_RESET}")
    return True


def handle_command(interp, raw):
    line = raw.strip()
    if not line:
        return True

    upper = line.upper()

    # Numbered line
    parts = line.split(None, 1)
    if parts[0].isdigit():
        num  = int(parts[0])
        text = parts[1].upper() if len(parts) > 1 else ""
        interp.add_line(num, text)
        return True

    # Commands
    if upper == "RUN":
        interp.run()
        return True

    if upper == "LIST":
        print(interp.list_program())
        return True

    if upper in ("NEW", "CLR" if upper == "NEW" else ""):
        interp.new_program()
        print(f"{C_META}OK{C_RESET}")
        return True

    if upper == "CLR":
        interp.clr_vars()
        print(f"{C_META}OK{C_RESET}")
        return True

    if upper.startswith("LOAD"):
        arg = line[4:].strip().strip('"').strip("'").strip()
        if not arg:
            print(f"{C_META}AVAILABLE SAMPLES:{C_RESET}")
            for k in SAMPLES:
                print(f"  {C_PROMPT}{k}{C_RESET}")
        else:
            # Try file first, then built-in
            fname = arg if arg.endswith(".bas") else arg + ".bas"
            if os.path.exists(fname):
                interp.new_program()
                with open(fname) as f:
                    for ln in f:
                        ln = ln.rstrip()
                        parts2 = ln.split(None, 1)
                        if parts2 and parts2[0].isdigit():
                            interp.add_line(int(parts2[0]), (parts2[1].upper() if len(parts2) > 1 else ""))
                print(f"{C_META}LOADED: {fname}{C_RESET}")
            else:
                load_sample(interp, arg)
        return True

    if upper.startswith("SAVE"):
        arg = line[4:].strip().strip('"').strip("'").strip()
        if not arg:
            print(f"{C_ERROR}?MISSING FILENAME{C_RESET}")
            return True
        fname = arg if arg.endswith(".bas") else arg + ".bas"
        with open(fname, "w") as f:
            for n in interp.sorted_keys():
                f.write(f"{n} {interp.lines[n]}\n")
        print(f"{C_META}SAVED: {fname}{C_RESET}")
        return True

    if upper == "DIR":
        files = sorted(f for f in os.listdir(".") if f.endswith(".bas"))
        if files:
            print(f"{C_META}BAS FILES IN CURRENT DIRECTORY:{C_RESET}")
            for f in files:
                print(f"  {C_PROMPT}{f}{C_RESET}")
        else:
            print(f"{C_META}NO .BAS FILES FOUND{C_RESET}")
        return True

    if upper == "HELP":
        print(HELP_TEXT)
        return True

    if upper in ("EXIT", "BYE", "QUIT"):
        print(f"{C_META}BYE!{C_RESET}")
        return False

    # Immediate mode: run as line 0
    upper_cmd = line.upper()
    interp.add_line(0, upper_cmd)
    interp.run(start_line=0)
    if 0 in interp.lines:
        del interp.lines[0]
        interp._sorted_keys = None
    return True


def repl():
    interp = Interpreter()
    print(BOOT_MSG)

    while True:
        try:
            raw = input(f"{C_PROMPT}>{C_RESET} ")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C_META}BYE!{C_RESET}")
            break
        if not handle_command(interp, raw):
            break


def run_file(path):
    interp = Interpreter()
    if not os.path.exists(path):
        print(f"{C_ERROR}?FILE NOT FOUND: {path}{C_RESET}")
        sys.exit(1)
    with open(path) as f:
        for ln in f:
            ln = ln.rstrip()
            parts = ln.split(None, 1)
            if parts and parts[0].isdigit():
                interp.add_line(int(parts[0]), (parts[1].upper() if len(parts) > 1 else ""))
    interp.run()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        repl()
