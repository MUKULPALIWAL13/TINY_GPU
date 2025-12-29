import cocotb
from cocotb.triggers import RisingEdge
from .helpers.setup import setup
from .helpers.memory import Memory
from .helpers.format import format_cycle
from .helpers.logger import logger


@cocotb.test()
async def test_kernel1_mul(dut):

    program_memory = Memory(dut=dut, addr_bits=8, data_bits=16,
                            channels=1, name="program")

    #
    # KERNEL #1: C[0] = A[0] * B[0]
    #
    program = [
        0b1001000100000000,  # CONST R1, #0
        0b1001001000001000,  # CONST R2, #8
        0b1001001100010000,  # CONST R3, #16

        0b0111010000010000,  # LDR R4, R1
        0b0111010100100000,  # LDR R5, R2

        0b0101011001000101,  # MUL R6, R4, R5

        0b1000000000110110,  # STR R3, R6

        0b1111000000000000,  # RET
    ]

    data_memory = Memory(dut=dut, addr_bits=8, data_bits=8,
                         channels=4, name="data")

    #
    # Data layout:
    # A = [2, 4, 6, 5, 8, 9, 4, 3]
    # B = [1, 1, 1, 1, 1, 1, 1, 1]
    #
    A = [2,4,6,5,8,9,4,3]
    B = [1,1,1,1,1,1,1,1]

    threads = 1

    await setup(
        dut=dut,
        program_memory=program_memory,
        program=program,
        data_memory=data_memory,
        data=A+B,
        threads=threads,
    )

    cycles = 0
    while dut.done.value != 1 and cycles < 200:
     data_memory.run()
     program_memory.run()
    await cocotb.triggers.ReadOnly()
    await RisingEdge(dut.clk)
    cycles += 1

    assert cycles < 200, "Kernel likely stuck — RET never executed"

    logger.info(f"Completed in {cycles} cycles")

    #
    # RESULT: C starts at address 16
    #
    result = data_memory.memory[16]

    print("C[0] =", result)
    assert result == A[0] * B[0], f"expected {A[0]*B[0]}, got {result}"
