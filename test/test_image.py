import cocotb
from cocotb.triggers import RisingEdge
from .helpers.setup import setup
from .helpers.memory import Memory
from .helpers.format import format_cycle
from .helpers.logger import logger

LOGFILE = open("grayscale_run.log", "w")


# ---------------- MINI ASSEMBLER ----------------

def R(x):
    return int(x[1:])   # "R7" -> 7


def assemble(asm):
    lines = []
    for l in asm.splitlines():
        l = l.split(";")[0].strip()
        if l:
            lines.append(l)

    labels = {}
    pc = 0

    # First pass: collect labels
    for l in lines:
        if l.endswith(":"):
            labels[l[:-1]] = pc
        else:
            pc += 1

    code = []

    # Second pass: encode instructions
    for l in lines:
        if l.endswith(":"):
            continue

        p = l.replace(",", "").split()
        op = p[0]

        if op == "CONST":
            code.append(0b1001000000000000 | (R(p[1]) << 8) | int(p[2][1:]))

        elif op == "ADD":
            code.append(0b0011000000000000 | (R(p[1]) << 8) | (R(p[2]) << 4) | R(p[3]))

        elif op == "SUB":
            code.append(0b0100000000000000 | (R(p[1]) << 8) | (R(p[2]) << 4) | R(p[3]))

        elif op == "MUL":
            code.append(0b0101000000000000 | (R(p[1]) << 8) | (R(p[2]) << 4) | R(p[3]))

        elif op == "DIV":
            code.append(0b0110000000000000 | (R(p[1]) << 8) | (R(p[2]) << 4) | R(p[3]))

        elif op == "LDR":
            code.append(0b0111000000000000 | (R(p[1]) << 8) | (R(p[2]) << 4))

        elif op == "STR":
            code.append(0b1000000000000000 | (R(p[1]) << 4) | R(p[2]))

        elif op == "CMP":
            code.append(0b0010000000000000 | (R(p[1]) << 4) | R(p[2]))

        elif op == "BRn":
            code.append(0b0001100000000000 | labels[p[1]])

        elif op == "RET":
            code.append(0b1111000000000000)

        else:
            raise ValueError(f"Unknown opcode {op}")

    return code


# ---------------- GRAYSCALE ASM (8 PIXELS) ----------------

ASM = """
; i = blockIdx * blockDim + threadIdx
MUL R0, R13, R14
ADD R0, R0, R15

; base pointers
CONST R1, #0      ; baseRGB
CONST R2, #24     ; baseGray

; addrRGB = baseRGB + 3*i
ADD R3, R0, R0
ADD R3, R3, R0
ADD R3, R3, R1

; load R, G, B
LDR R4, R3
CONST R7, #1
ADD R3, R3, R7
LDR R5, R3
ADD R3, R3, R7
LDR R6, R3

; gray = (R/4) + (G/2) + (B/8)
CONST R7, #4
DIV R4, R4, R7

CONST R7, #2
DIV R5, R5, R7

CONST R7, #8
DIV R6, R6, R7

ADD R4, R4, R5
ADD R4, R4, R6

; store gray (DO NOT modify base register)
ADD R7, R2, R0
STR R7, R4

RET
"""


# ---------------- TEST ----------------

@cocotb.test()
async def test_grayscale_8(dut):

    program = assemble(ASM)

    program_memory = Memory(
        dut=dut, addr_bits=8, data_bits=16, channels=1, name="program"
    )

    data_memory = Memory(
        dut=dut, addr_bits=8, data_bits=8, channels=4, name="data"
    )

    # 8 RGB pixels
    data = [
        255, 0,   0,     # red
        0,   255, 0,     # green
        0,   0,   255,   # blue
        255, 255, 255,  # white
        0,   0,   0,     # black
        128, 128, 128,  # gray
        50,  100, 150,
        10,  20,  30,
    ] + [0]*8   # output space

    await setup(
        dut=dut,
        program_memory=program_memory,
        program=program,
        data_memory=data_memory,
        data=data,
        threads=8,
    )

    cycles = 0
    while dut.done.value != 1:
        data_memory.run()
        program_memory.run()

        await cocotb.triggers.ReadOnly()
        format_cycle(dut, cycles)
        logger.info(f"cycle {cycles}")

        await RisingEdge(dut.clk)
        cycles += 1

        if cycles > 2000:
            raise RuntimeError("Timeout: possible infinite loop")

    logger.info(f"Completed in {cycles} cycles")
    print(f"Completed in {cycles} cycles", file=LOGFILE)

    gray = [data_memory.memory[i + 24] for i in range(8)]
    print("FINAL RESULT (GRAY):", gray)
    logger.info(f"FINAL RESULT (GRAY): {gray}")
    print("FINAL RESULT (GRAY):", gray, file=LOGFILE)

    LOGFILE.close()
