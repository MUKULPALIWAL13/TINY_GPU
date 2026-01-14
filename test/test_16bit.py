import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock
from .helpers.memory import Memory
from .helpers.setup import setup

from PIL import Image
import numpy as np
import os


# ---------------- MINI ASSEMBLER ----------------

def R(x):
    return int(x[1:])


def assemble(asm):
    code = []
    for line in asm.splitlines():
        line = line.split(";")[0].strip()
        if not line:
            continue

        p = line.replace(",", "").split()
        op = p[0]

        if op == "CONST":
            code.append(0b1001000000000000 | (R(p[1]) << 8) | int(p[2][1:]))
        elif op == "ADD":
            code.append(0b0011000000000000 | (R(p[1]) << 8) | (R(p[2]) << 4) | R(p[3]))
        elif op == "MUL":
            code.append(0b0101000000000000 | (R(p[1]) << 8) | (R(p[2]) << 4) | R(p[3]))
        elif op == "DIV":
            code.append(0b0110000000000000 | (R(p[1]) << 8) | (R(p[2]) << 4) | R(p[3]))
        elif op == "LDR":
            code.append(0b0111000000000000 | (R(p[1]) << 8) | (R(p[2]) << 4))
        elif op == "STR":
            code.append(0b1000000000000000 | (R(p[1]) << 4) | R(p[2]))
        elif op == "RET":
            code.append(0b1111000000000000)
        else:
            raise ValueError("Unknown opcode: " + op)

    return code


# ---------------- GRAYSCALE KERNEL ----------------
# gray = (R>>2) + (G>>1) + (B>>3)

ASM = """
MUL R0, R13, R14
ADD R0, R0, R15

CONST R1, #0
CONST R2, #768

ADD R3, R0, R0
ADD R3, R3, R0
ADD R3, R3, R1

LDR R4, R3
CONST R7, #1
ADD R3, R3, R7
LDR R5, R3
ADD R3, R3, R7
LDR R6, R3

ADD R5, R5, R5      ; 2*G
ADD R4, R4, R5      ; R + 2*G
ADD R4, R4, R6      ; R + 2*G + B

CONST R7, #4
DIV R4, R4, R7      ; >> 2
ADD R7, R2, R0
STR R7, R4

RET
"""


# ---------------- TEST ----------------

@cocotb.test()
async def test_grayscale_16x16(dut):

    # Clock
    clock = Clock(dut.clk, 25, units="us")
    cocotb.start_soon(clock.start())

    # Memories
    program_memory = Memory(dut, 8, 16, 1, "program")
    data_memory = Memory(dut, 8, 8, 4, "data")

    program = assemble(ASM)

    # Load image
    here = os.path.dirname(__file__)
    img = Image.open(os.path.join(here, "input.jpeg")).resize((16, 16))
    rgb = np.array(img).astype(np.uint8).flatten().tolist()

    # -------------------------------------------------
    # PRE-ALLOCATE DATA MEMORY (CRITICAL FIX)
    # -------------------------------------------------
    DATA_MEM_SIZE = 1024
    data = rgb + [0] * (DATA_MEM_SIZE - len(rgb))

    THREADS = 16
    BLOCKS = 16

    # Setup ONCE
    await setup(
        dut,
        program_memory,
        program,
        data_memory,
        data,
        threads=THREADS,
        block_idx=0,
    )

    # ---- FORCE MEMORY LIST TO FULL SIZE ----
    if len(data_memory.memory) < DATA_MEM_SIZE:
        data_memory.memory.extend([0] * (DATA_MEM_SIZE - len(data_memory.memory)))

    # Ensure start is low
    dut.start.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    # Run blocks
    for block in range(BLOCKS):

        # write blockIdx
        dut.device_control_write_enable.value = 1
        dut.device_control_data.value = block
        await RisingEdge(dut.clk)
        dut.device_control_write_enable.value = 0
        await RisingEdge(dut.clk)

        # start pulse
        dut.start.value = 1
        await RisingEdge(dut.clk)
        dut.start.value = 0

        # wait for done
        cycles = 0
        while dut.done.value != 1:
            data_memory.run()
            program_memory.run()
            await RisingEdge(dut.clk)
            cycles += 1
            if cycles > 5000:
                raise RuntimeError("Timeout in block " + str(block))

        print(f"Block {block} finished")

        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
    
    # -------------------------------------------------
    # READ BACK RESULT (NOW SAFE)
    # -------------------------------------------------
    gray = np.array(data_memory.memory[768:768+256], dtype=np.uint8)
    print("Gray buffer length:", len(gray))

    Image.fromarray(gray.reshape(16, 16), mode="L").save("output.png")
    print("output.png written")
# ---- DEBUG: DUMP RAW GRAYSCALE VECTOR ----
    gray = data_memory.memory[768:768+256]

    print("RAW GRAYSCALE VECTOR (first 64 values):")
    for i in range(0, 64, 8):
        print(gray[i:i+8])

    # also save full vector to file
    with open("gray_vector.txt", "w") as f:
        for i, v in enumerate(gray):
            f.write(f"{i}: {v}\n")

    print("gray_vector.txt written")