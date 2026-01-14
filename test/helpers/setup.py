from typing import List
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from .memory import Memory

_clock_started = False   # <-- IMPORTANT


async def setup(
    dut,
    program_memory: Memory,
    program: List[int],
    data_memory: Memory,
    data: List[int],
    threads: int,
    block_idx=0,
):
    global _clock_started

    # -------------------------------------------------
    # Start clock ONCE
    # -------------------------------------------------
    if not _clock_started:
        clock = Clock(dut.clk, 25, units="us")
        cocotb.start_soon(clock.start())
        _clock_started = True

    # -------------------------------------------------
    # Reset ONCE
    # -------------------------------------------------
    dut.reset.value = 1
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await RisingEdge(dut.clk)

    # -------------------------------------------------
    # Load memories ONCE
    # -------------------------------------------------
    program_memory.load(program)
    data_memory.load(data)

    # -------------------------------------------------
    # Write blockDim (threads per block)
    # -------------------------------------------------
    dut.device_control_write_enable.value = 1
    dut.device_control_data.value = threads
    await RisingEdge(dut.clk)
    dut.device_control_write_enable.value = 0

    # -------------------------------------------------
    # Write initial blockIdx (usually 0)
    # -------------------------------------------------
    dut.device_control_write_enable.value = 1
    dut.device_control_data.value = block_idx
    await RisingEdge(dut.clk)
    dut.device_control_write_enable.value = 0
