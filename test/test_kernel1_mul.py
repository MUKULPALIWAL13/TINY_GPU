import cocotb
from cocotb.triggers import RisingEdge, ReadOnly
from PIL import Image
import numpy as np

from .helpers.setup import setup
from .helpers.memory import Memory
from .helpers.format import format_cycle
from .helpers.logger import logger


@cocotb.test()
async def test_grayscale_fixed_point(dut):

    # --------------------------------------------------
    # Load image on host
    # --------------------------------------------------
    img = Image.open("input.jpeg").convert("RGB")
    width, height = img.size
    pixels = np.array(img).reshape(-1, 3)

    rgb_flat = []
    for r, g, b in pixels:
        rgb_flat.extend([int(r), int(g), int(b)])

    num_pixels = len(pixels)

    # --------------------------------------------------
    # Program memory (GPU kernel)
    # --------------------------------------------------
    program_memory = Memory(
        dut=dut, addr_bits=8, data_bits=16, channels=1, name="program"
    )

    program = [
        0b0101000011011110,  # MUL R0, %blockIdx, %blockDim
        0b0011000000001111,  # ADD R0, R0, %threadIdx        ; i

        0b1001000100010011,  # CONST R1, #299
        0b1001001000100101,  # CONST R2, #587
        0b1001001100001110,  # CONST R3, #114

        0b1001010000000000,  # CONST R4, #0      ; rgb_base
        0b1001010101000000,  # CONST R5, #64     ; gray_base

        0b0101100000000011,  # MUL R6, R0, R3    ; addr = i * 3
        0b0011101101100100,  # ADD R6, R6, R4

        0b0111100110000000,  # LDR R7, R6        ; R
        0b1001001100000001,  # CONST R3, #1
        0b0011101101100011,  # ADD R6, R6, R3
        0b0111101000000000,  # LDR R8, R6        ; G
        0b0011101101100011,  # ADD R6, R6, R3
        0b0111101001000000,  # LDR R9, R6        ; B

        0b0101110101110001,  # MUL R10, R7, R1   ; 299*R
        0b0101110110000010,  # MUL R11, R8, R2   ; 587*G
        0b0011101010101011,  # ADD R10, R10, R11
        0b0101110110010011,  # MUL R11, R9, R3   ; 114*B
        0b0011101010101011,  # ADD R10, R10, R11

        0b0011100101010000,  # ADD R9, R5, R0
        0b1000000010011010,  # STR R9, R10

        0b1111000000000000   # RET
    ]

    # --------------------------------------------------
    # Data memory
    # --------------------------------------------------
    data_memory = Memory(
        dut=dut, addr_bits=8, data_bits=32, channels=1, name="data"
    )

    # RGB data first, grayscale output after
    data = rgb_flat + [0] * num_pixels

    # --------------------------------------------------
    # Launch GPU
    # --------------------------------------------------
    threads = num_pixels

    await setup(
        dut=dut,
        program_memory=program_memory,
        program=program,
        data_memory=data_memory,
        data=data,
        threads=threads
    )

    # --------------------------------------------------
    # Run simulation
    # --------------------------------------------------
    cycles = 0
    while dut.done.value != 1:
        data_memory.run()
        program_memory.run()

        await ReadOnly()
        format_cycle(dut, cycles, thread_id=0)

        await RisingEdge(dut.clk)
        cycles += 1

    logger.info(f"Completed in {cycles} cycles")

    # --------------------------------------------------
    # Read back grayscale accumulator
    # --------------------------------------------------
    gray_base = len(rgb_flat)
    gray_acc = data_memory.memory[gray_base:gray_base + num_pixels]

    # --------------------------------------------------
    # Convert back to image (HOST SIDE)
    # --------------------------------------------------
    gray = (np.array(gray_acc) // 1000).astype(np.uint8)
    gray_img = gray.reshape(height, width)

    Image.fromarray(gray_img, mode="L").save("grayscale_output.png")

    logger.info("Grayscale image generated successfully")