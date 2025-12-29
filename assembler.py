# assembler.py
import re

REG = lambda r: int(r.replace("R", ""))

def assemble_line(op, args, labels, pc):
    if op == "CONST":
        d, imm = args
        return 0b1001000000000000 | (REG(d) << 8) | int(imm.replace("#", ""))
    
    if op == "ADD":
        d, s, t = args
        return 0b0011000000000000 | (REG(d) << 8) | (REG(s) << 4) | REG(t)

    if op == "MUL":
        d, s, t = args
        return 0b0101000000000000 | (REG(d) << 8) | (REG(s) << 4) | REG(t)

    if op == "LDR":
        d, s = args
        return 0b0111000000000000 | (REG(d) << 8) | (REG(s) << 4)

    if op == "STR":
        d, s = args
        return 0b1000000000000000 | (REG(d) << 4) | REG(s)

    if op == "CMP":
        s, t = args
        return 0b0010000000000000 | (REG(s) << 4) | REG(t)

    if op == "BRn":
        label = args[0]
        return 0b0001100000000000 | labels[label]

    if op == "RET":
        return 0b1111000000000000

    raise ValueError(f"Unknown op {op}")


def assemble(program_text):
    lines = [l.split(";")[0].strip() for l in program_text.splitlines()]
    lines = [l for l in lines if l]

    labels = {}
    pc = 0

    # First pass: collect labels
    for line in lines:
        if line.endswith(":"):
            labels[line[:-1]] = pc
        else:
            pc += 1

    # Second pass: encode
    pc = 0
    machine = []

    for line in lines:
        if line.endswith(":"):
            continue

        parts = re.split(r"[,\s]+", line)
        op = parts[0]
        args = parts[1:]

        word = assemble_line(op, args, labels, pc)
        machine.append(word)
        pc += 1

    return machine
asm = """
CONST R1, #0
CONST R2, #8
CONST R3, #16
CONST R6, #0
CONST R7, #0
CONST R0, #1

LOOP:
ADD R4, R1, R7
LDR R4, R4
ADD R5, R2, R7
LDR R5, R5
MUL R8, R4, R5
ADD R6, R6, R8
ADD R7, R7, R0
CONST R4, #4
CMP R7, R4
BRn LOOP

STR R3, R6
RET
"""

print(assemble(asm))
code = assemble(asm)

print("BINARY:")
for w in code:
    print(format(w, "016b"))