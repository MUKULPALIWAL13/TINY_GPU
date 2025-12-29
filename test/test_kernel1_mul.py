import cocotb
from cocotb.triggers import RisingEdge
from .helpers.setup import setup
from .helpers.memory import Memory
from .helpers.format import format_cycle
from .helpers.logger import logger


LOGFILE = open("matmul_run.log", "w")


@cocotb.test()
async def test_matmul(dut):

    # -------- PROGRAM MEMORY --------
    program_memory = Memory(dut=dut, addr_bits=8, data_bits=16, channels=1, name="program")

    # Dot-product loop kernel
    program = [

        # base pointers
        0b1001000100000000,   # CONST R1, #0      ; baseA
        0b1001001000001000,   # CONST R2, #8      ; baseB
        0b1001001100010000,   # CONST R3, #16     ; baseC

        # acc = 0
        0b1001011000000000,   # CONST R6, #0

        # k = 0
        0b1001011100000000,   # CONST R7, #0

        # inc = 1
        0b1001000000000001,   # CONST R0, #1

        # -------- LOOP START (PC = 6) --------

        # addrA = baseA + k
        0b0011010000010111,   # ADD R4, R1, R7
        0b0111010001000000,   # LDR R4, R4        ; A[k]

        # addrB = baseB + k
        0b0011010100100111,   # ADD R5, R2, R7
        0b0111010101010000,   # LDR R5, R5        ; B[k]

        # tmp = A * B   (R8)
        0b0101100001000101,   # MUL R8, R4, R5

        # acc += tmp
        0b0011011001101000,   # ADD R6, R6, R8

        # k += 1
        0b0011011101110000,   # ADD R7, R7, R0

        # compare k < 4
        0b1001010000000100,    # CONST R4, #4
        0b0010000001110100,   # CMP R7, R4

        # branch back if still k < 4
        0b0001100000000110,   # BRn LOOP

        # -------- STORE RESULT --------
        0b1000000000110110,   # STR R3, R6
        0b1111000000000000,   # RET
    ]

    # -------- DATA MEMORY --------
    data_memory = Memory(dut=dut, addr_bits=8, data_bits=8, channels=4, name="data")

    data = [
        2,4,6,5,8,9,4,3,      # A
        1,1,1,1,1,1,1,1      # B
    ]

    threads = 8   # still unused — only C[0] is produced

    await setup(
        dut=dut,
        program_memory=program_memory,
        program=program,
        data_memory=data_memory,
        data=data,
        threads=threads
    )

    data_memory.display(24)

    cycles = 0
    while dut.done.value != 1:
        data_memory.run()
        program_memory.run()
        await cocotb.triggers.ReadOnly()
        format_cycle(dut, cycles)
        await RisingEdge(dut.clk)
        cycles += 1

    msg = f"Completed in {cycles} cycles"
    logger.info(msg)
    print(msg, file=LOGFILE)

    # ---- FINAL RESULT ----
    c_values = [data_memory.memory[i + 16] for i in range(8)]

    print("FINAL RESULT (C):", c_values)
    logger.info(f"FINAL RESULT (C): {c_values}")
    print("FINAL RESULT (C): " + str(c_values), file=LOGFILE)

    with open("matmul_result.txt", "w") as f:
        f.write(" ".join(map(str, c_values)))

    LOGFILE.close()
