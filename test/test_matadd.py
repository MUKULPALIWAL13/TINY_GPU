import cocotb
from cocotb.triggers import RisingEdge
from .helpers.setup import setup
from .helpers.memory import Memory
from .helpers.format import format_cycle
from .helpers.logger import logger


# Write our own simple run log
LOGFILE = open("matadd_run.log", "w")


@cocotb.test()
async def test_matadd(dut):
    # Program Memory
    program_memory = Memory(dut=dut, addr_bits=8, data_bits=16, channels=1, name="program")
    program = [
        0b0101000011011110,
        0b0011000000001111,
        0b1001000100000000,
        0b1001001000001000,
        0b1001001100010000,
        0b0011010000010000,
        0b0111010001000000,
        0b0011010100100000,
        0b0111010101010000,
        0b0011011001000101,
        0b0011011100110000,
        0b1000000001110110,
        0b1111000000000000,
    ]

    # Data Memory (A then B)
    data_memory = Memory(dut=dut, addr_bits=8, data_bits=8, channels=4, name="data")
    data = [
        0, 1, 2, 3, 4, 5, 6, 7,
        0, 4, 7, 8, 6, 5, 2, 1
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

    data_memory.display(24)

    # ---- FINAL RESULT (Matrix C lives at offsets 16..23) ----
    c_values = [data_memory.memory[i + 16] for i in range(8)]

    print("FINAL RESULT (C):", c_values)
    logger.info(f"FINAL RESULT (C): {c_values}")
    print("FINAL RESULT (C): " + str(c_values), file=LOGFILE)

    # Save result to file
    with open("matadd_result.txt", "w") as f:
        f.write(" ".join(map(str, c_values)))

    # Assertions
    expected_results = [a + b for a, b in zip(data[0:8], data[8:16])]
    for i, expected in enumerate(expected_results):
        result = data_memory.memory[i + 16]
        assert result == expected, f"Result mismatch at index {i}: expected {expected}, got {result}"

    LOGFILE.close()
