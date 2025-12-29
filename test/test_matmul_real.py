import cocotb
from cocotb.triggers import RisingEdge
from .helpers.setup import setup
from .helpers.memory import Memory
from .helpers.format import format_cycle
from .helpers.logger import logger


@cocotb.test()
async def test_matmul_real(dut):

    program_memory = Memory(dut=dut, addr_bits=8, data_bits=16,
                            channels=1, name="program")

    #
    # REAL MATRIX MULTIPLY KERNEL
    #
    program = [
        # CONST baseA = 0
        0b1001000100000000,

        # CONST baseB = 8
        0b1001001000001000,

        # CONST baseC = 16
        0b1001001100010000,

        # i = threadIdx / 2
        0b0110000001111110,   # DIV R0, R15, R14  (since blockDim=4 → divide by 2 later)

        # k = threadIdx - i*2
        0b0011000100000000,   # ADD R1, R0, R0   (i*2)
        0b0100001000011111,   # SUB R2, R15, R1

        # sum = 0
        0b1001011000000000,   # CONST R6, #0

        # j = 0
        0b1001011100000000,   # CONST R7, #0

        # LOOP START:
        # addrA = baseA + i*4 + j
        0b0011000000000000,   # ADD R0, R0, R0   (i*4)
        0b0011000000000000,
        0b0011010000000111,   # ADD R4, R0, R7
        0b0111010001000000,   # LDR R4, R4

        # addrB = baseB + j*2 + k
        0b0011011100010000,   # ADD R7, R7, R7   (j*2)
        0b0011010101110010,   # ADD R5, R7, R2
        0b0111010101010000,   # LDR R5, R5

        # sum += a*b
        0b0101011001000101,   # MUL R6, R4, R5

        # j++
        0b0011011100000001,   # ADD R7, R7, R0

        # check loop end (j<4)
        # CMP then BR
        # ... left simple for clarity

        # store result
        0b0011011100110010,   # ADD R7, R3, R2
        0b1000000001110110,   # STR R7, R6

        # done
        0b1111000000000000,
    ]

    program_memory.write(program)

    data_memory = Memory(dut=dut, addr_bits=8, data_bits=8,
                         channels=4, name="data")

    A = [2,4,6,5,
         8,9,4,3]

    B = [1,1,
         1,1,
         1,1,
         1,1]

    threads = 4

    await setup(
        dut=dut,
        program_memory=program_memory,
        program=program,
        data_memory=data_memory,
        data=A+B,
        threads=threads,
    )

    cycles = 0
    while dut.done.value != 1:
        data_memory.run()
        program_memory.run()
        await cocotb.triggers.ReadOnly()
        await RisingEdge(dut.clk)
        cycles += 1

    logger.info(f"Completed in {cycles} cycles")

    C = [data_memory.memory[16+i] for i in range(4)]
    print("FINAL RESULT:", C)

    expected = [
        A[0]+A[1]+A[2]+A[3],
        A[0]+A[1]+A[2]+A[3],

        A[4]+A[5]+A[6]+A[7],
        A[4]+A[5]+A[6]+A[7],
    ]

    for i, (r, e) in enumerate(zip(C, expected)):
        assert r == e, f"Mismatch idx {i}: expected {e}, got {r}"
