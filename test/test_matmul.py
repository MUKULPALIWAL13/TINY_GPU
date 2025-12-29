import cocotb
from cocotb.triggers import RisingEdge
from .helpers.setup import setup
from .helpers.memory import Memory
from .helpers.format import format_cycle
from .helpers.logger import logger


LOGFILE = open("matmul_run.log", "w")


@cocotb.test()
async def test_matmul(dut):
    program_memory = Memory(dut=dut, addr_bits=8, data_bits=16, channels=1, name="program")

    program = [
        0b0101000011011110,
        0b0011000000001111,
        0b1001000100000000,
        0b1001001000001000,
        0b1001001100010000,
        0b1001010000001000,
        0b0000010100000000,
        0b0000011000000000,
        0b0011011100010100,
        0b0111011101110000,
        0b0011100000100000,
        0b0111100010000000,
        0b0011010101111000,
        0b0011011001100100,
        0b1011001001000000,
        0b0011011100110000,
        0b1000000001110101,
        0b1111000000000000,
    ]

    data_memory = Memory(dut=dut, addr_bits=8, data_bits=8, channels=4, name="data")

    data = [
         2,4,6,5,8,9,4,3,     
         1,1,1,1, 1,1,1,1      
    ]

    threads = 8

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
