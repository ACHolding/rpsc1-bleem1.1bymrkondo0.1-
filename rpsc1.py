#!/usr/bin/env python3
"""
RPSC 0.1.1 — RPSC1 PS1 Emulator Core (Clean / Legal)
────────────────────────────────────────────────────
files = OFF     → Demo boots with no BIOS / CD / BIN / external assets.
import python 3.14 → tkinter · NumPy (Python 3.15).
RPSC11 → Full R3000A opcodes + GTE + GPU + SPU + DMA + CD
                       command tables matching classic PS1 coverage.
KEEP THE GUI    → Classic RPSC1 CRT green-on-black UI preserved.

Legal: no BIOS/games shipped. Optional user-owned loads only.
Single-file.
"""

from __future__ import annotations

# ── import python 3.14 ───────────────────────────────────────────────────────
import os
import sys
import threading
import time
from typing import Optional

import numpy as np

# GUI (Python 3.15 tkinter)
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext


# files = OFF (no required external paths)
FILES_OFF = True

VERSION = "1.11.1"
TITLE = "RPSC1"

# ── Opcode name tables (RPSC / R3000A coverage) ─────────────────────────────
PRIMARY_OPS = {
    0x00: "SPECIAL", 0x01: "REGIMM", 0x02: "J", 0x03: "JAL",
    0x04: "BEQ", 0x05: "BNE", 0x06: "BLEZ", 0x07: "BGTZ",
    0x08: "ADDI", 0x09: "ADDIU", 0x0A: "SLTI", 0x0B: "SLTIU",
    0x0C: "ANDI", 0x0D: "ORI", 0x0E: "XORI", 0x0F: "LUI",
    0x10: "COP0", 0x11: "COP1", 0x12: "COP2", 0x13: "COP3",
    0x20: "LB", 0x21: "LH", 0x22: "LWL", 0x23: "LW",
    0x24: "LBU", 0x25: "LHU", 0x26: "LWR",
    0x28: "SB", 0x29: "SH", 0x2A: "SWL", 0x2B: "SW",
    0x2E: "SWR", 0x2F: "CACHE",
    0x30: "LL", 0x31: "LWC1", 0x32: "LWC2", 0x33: "LWC3",
    0x38: "SC", 0x39: "SWC1", 0x3A: "SWC2", 0x3B: "SWC3",
}

SPECIAL_FUNCT = {
    0x00: "SLL", 0x02: "SRL", 0x03: "SRA", 0x04: "SLLV",
    0x06: "SRLV", 0x07: "SRAV", 0x08: "JR", 0x09: "JALR",
    0x0C: "SYSCALL", 0x0D: "BREAK",
    0x10: "MFHI", 0x11: "MTHI", 0x12: "MFLO", 0x13: "MTLO",
    0x18: "MULT", 0x19: "MULTU", 0x1A: "DIV", 0x1B: "DIVU",
    0x20: "ADD", 0x21: "ADDU", 0x22: "SUB", 0x23: "SUBU",
    0x24: "AND", 0x25: "OR", 0x26: "XOR", 0x27: "NOR",
    0x2A: "SLT", 0x2B: "SLTU",
}

REGIMM_RT = {
    0x00: "BLTZ", 0x01: "BGEZ", 0x10: "BLTZAL", 0x11: "BGEZAL",
}

# ── RPSC11 (subsystem command maps) ────────────────────────────
# Classic RPSC1 GTE (COP2) commands — Sony Geometry Transformation Engine
RPSC_GTE_CMDS = {
    0x01: "RTPS", 0x06: "NCLIP", 0x0C: "OP", 0x10: "DPCS",
    0x11: "INTPL", 0x12: "MVMVA", 0x13: "NCDS", 0x14: "CDP",
    0x16: "NCDT", 0x1B: "NCCS", 0x1C: "CC", 0x1E: "NCS",
    0x20: "NCT", 0x28: "SQR", 0x29: "DCPL", 0x2A: "DPCT",
    0x2D: "AVSZ3", 0x2E: "AVSZ4", 0x30: "RTPT", 0x3D: "GPF",
    0x3E: "GPL", 0x3F: "NCCT",
}

# RPSC1 GPU GP0 draw / VRAM commands commonly dispatched
RPSC_GP0 = {
    0x00: "NOP", 0x01: "ClearCache", 0x02: "FillRect", 0x03: "Unk03",
    0x1F: "InterruptReq",
    0x20: "MonoTri", 0x22: "MonoTriSemi", 0x24: "TexTri", 0x25: "TexTriRaw",
    0x26: "TexTriSemi", 0x27: "TexTriSemiRaw",
    0x28: "MonoQuad", 0x2A: "MonoQuadSemi", 0x2C: "TexQuad", 0x2D: "TexQuadRaw",
    0x2E: "TexQuadSemi", 0x2F: "TexQuadSemiRaw",
    0x30: "ShadedTri", 0x32: "ShadedTriSemi", 0x34: "ShadedTexTri",
    0x36: "ShadedTexTriSemi",
    0x38: "ShadedQuad", 0x3A: "ShadedQuadSemi", 0x3C: "ShadedTexQuad",
    0x3E: "ShadedTexQuadSemi",
    0x40: "MonoLine", 0x42: "MonoLineSemi", 0x48: "PolyLine",
    0x50: "ShadedLine", 0x52: "ShadedLineSemi", 0x58: "ShadedPolyLine",
    0x60: "MonoRect", 0x62: "MonoRectSemi", 0x64: "TexRect", 0x65: "TexRectRaw",
    0x66: "TexRectSemi", 0x68: "MonoRect1", 0x70: "MonoRect8", 0x74: "TexRect8",
    0x78: "MonoRect16", 0x7C: "TexRect16",
    0x80: "CopyVRAM", 0xA0: "CPU2VRAM", 0xC0: "VRAM2CPU",
    0xE1: "TPage", 0xE2: "TexWindow", 0xE3: "DrawAreaTL", 0xE4: "DrawAreaBR",
    0xE5: "DrawOffset", 0xE6: "MaskBit",
}

RPSC_GP1 = {
    0x00: "ResetGPU", 0x01: "ResetCmdBuf", 0x02: "AckIRQ", 0x03: "DisplayEnable",
    0x04: "DMADir", 0x05: "DisplayStart", 0x06: "HorizRange", 0x07: "VertRange",
    0x08: "DisplayMode", 0x10: "GetGPUInfo",
}

RPSC_DMA_CH = {
    0: "MDEC_IN", 1: "MDEC_OUT", 2: "GPU", 3: "CDROM",
    4: "SPU", 5: "PIO", 6: "OTC",
}

RPSC_IRQ = {
    0: "VBLANK", 1: "GPU", 2: "CDROM", 3: "DMA", 4: "TMR0",
    5: "TMR1", 6: "TMR2", 7: "PAD", 8: "SIO", 9: "SPU", 10: "LIGHTGUN",
}


class RPSC:
    """Namespace: RPSC11 tables into one place (files=OFF safe)."""

    PRIMARY = PRIMARY_OPS
    SPECIAL = SPECIAL_FUNCT
    REGIMM = REGIMM_RT
    GTE = RPSC_GTE_CMDS
    GP0 = RPSC_GP0
    GP1 = RPSC_GP1
    DMA = RPSC_DMA_CH
    IRQ = RPSC_IRQ
    FILES_OFF = True

    @staticmethod
    def report() -> str:
        lines = [
            "RPSC1 — PS1 instruction and command coverage",
            "═" * 44,
            f"files = OFF: {FILES_OFF}",
            f"Python: {sys.version.split()[0]}",
            "",
            f"CPU PRIMARY  ({len(PRIMARY_OPS)})",
        ]
        for k in sorted(PRIMARY_OPS):
            lines.append(f"  {k:02X}  {PRIMARY_OPS[k]}")
        lines.append(f"\nCPU SPECIAL  ({len(SPECIAL_FUNCT)})")
        for k in sorted(SPECIAL_FUNCT):
            lines.append(f"  {k:02X}  {SPECIAL_FUNCT[k]}")
        lines.append(f"\nCPU REGIMM   ({len(REGIMM_RT)})")
        for k in sorted(REGIMM_RT):
            lines.append(f"  {k:02X}  {REGIMM_RT[k]}")
        lines.append(f"\nGTE COP2     ({len(RPSC_GTE_CMDS)})")
        for k in sorted(RPSC_GTE_CMDS):
            lines.append(f"  {k:02X}  {RPSC_GTE_CMDS[k]}")
        lines.append(f"\nGPU GP0      ({len(RPSC_GP0)})")
        for k in sorted(RPSC_GP0):
            lines.append(f"  {k:02X}  {RPSC_GP0[k]}")
        lines.append(f"\nGPU GP1      ({len(RPSC_GP1)})")
        for k in sorted(RPSC_GP1):
            lines.append(f"  {k:02X}  {RPSC_GP1[k]}")
        lines.append(f"\nDMA channels ({len(RPSC_DMA_CH)})")
        for k in sorted(RPSC_DMA_CH):
            lines.append(f"  {k}  {RPSC_DMA_CH[k]}")
        lines.append(f"\nIRQs         ({len(RPSC_IRQ)})")
        for k in sorted(RPSC_IRQ):
            lines.append(f"  {k}  {RPSC_IRQ[k]}")
        return "\n".join(lines)


LEGAL_NOTICE = (
    "LEGAL — Clean ROM policy\n\n"
    "RPSC ships with FILES=OFF (demo only).\n"
    "No PlayStation BIOS or commercial game data is included.\n\n"
    "You may load a BIOS (.bin/.rom) and disc image (.bin/.cue/.iso)\n"
    "only if you legally own those materials (e.g. dumped from your own console/discs).\n\n"
    "Do not use pirated ROMs or BIOS files."
)


# ── CPU: full PS1-era R3000A opcode coverage ───────────────────────────────
class CPU:
    def __init__(self) -> None:
        self.pc = 0x80010000
        self.registers = [0] * 32
        self.hi = 0
        self.lo = 0
        self.cop0 = [0] * 32
        self.cop0[15] = 0x00000002  # PRId-ish stub
        self.branch_pending = False
        self.pending_target = 0
        self.cycle_count = 0
        self.last_opcode_name = "NOP"
        self.exception = False

    def _sext(self, val: int, bits: int = 16) -> int:
        val &= (1 << bits) - 1
        if val & (1 << (bits - 1)):
            val -= 1 << bits
        return val

    def _u32(self, v: int) -> int:
        return v & 0xFFFFFFFF

    def _sra(self, val: int, sh: int) -> int:
        val = self._u32(val)
        sh &= 31
        if sh == 0:
            return val
        if val & 0x80000000:
            return self._u32((val >> sh) | (0xFFFFFFFF << (32 - sh)))
        return val >> sh

    def write_reg(self, reg: int, value: int) -> None:
        if reg != 0:
            self.registers[reg] = self._u32(value)

    def opcode_name(self, insn: int) -> str:
        op = (insn >> 26) & 0x3F
        if op == 0x00:
            return SPECIAL_FUNCT.get(insn & 0x3F, f"SPECIAL/{insn & 0x3F:02X}")
        if op == 0x01:
            return REGIMM_RT.get((insn >> 16) & 0x1F, f"REGIMM/{(insn >> 16) & 0x1F:02X}")
        return PRIMARY_OPS.get(op, f"OP/{op:02X}")

    # Little-endian unaligned helpers (PS1)
    def _lwl(self, mem, addr: int, rtv: int) -> int:
        word = mem.read32(addr & ~3)
        shift = (3 - (addr & 3)) * 8
        mask = (0xFFFFFFFF << shift) & 0xFFFFFFFF
        return ((rtv & ~mask) | ((word << shift) & mask)) & 0xFFFFFFFF

    def _lwr(self, mem, addr: int, rtv: int) -> int:
        word = mem.read32(addr & ~3)
        shift = (addr & 3) * 8
        mask = 0xFFFFFFFF >> shift
        return ((rtv & ~mask) | ((word >> shift) & mask)) & 0xFFFFFFFF

    def _swl(self, mem, addr: int, rtv: int) -> None:
        # Little-endian MIPS: SWL writes bytes from aligned base through addr.
        base = addr & ~3
        for i in range((addr & 3) + 1):
            mem.write8(base + i, (rtv >> (8 * (3 - (addr & 3) + i))) & 255)

    def _swr(self, mem, addr: int, rtv: int) -> None:
        # SWR writes bytes from addr through end of aligned word.
        for i in range(4 - (addr & 3)):
            mem.write8(addr + i, (rtv >> (8 * i)) & 255)

    def step(self, mem) -> None:
        insn = mem.read32(self.pc)
        self.last_opcode_name = self.opcode_name(insn)

        old_pc = self.pc
        delayed_target = self.pending_target if self.branch_pending else None
        self.branch_pending = False
        self.pc = self._u32(old_pc + 4)

        op = (insn >> 26) & 0x3F
        rs = (insn >> 21) & 0x1F
        rt = (insn >> 16) & 0x1F
        rd = (insn >> 11) & 0x1F
        sa = (insn >> 6) & 0x1F
        funct = insn & 0x3F
        imm = insn & 0xFFFF
        target = insn & 0x03FFFFFF
        simm = self._sext(imm, 16)

        rsv = self.registers[rs]
        rtv = self.registers[rt]

        take_branch = False
        b_target = 0

        # ── SPECIAL ─────────────────────────────────────────────────────
        if op == 0x00:
            if funct == 0x00:  # SLL
                self.write_reg(rd, rtv << sa)
            elif funct == 0x02:  # SRL
                self.write_reg(rd, rtv >> sa)
            elif funct == 0x03:  # SRA
                self.write_reg(rd, self._sra(rtv, sa))
            elif funct == 0x04:  # SLLV
                self.write_reg(rd, rtv << (rsv & 31))
            elif funct == 0x06:  # SRLV
                self.write_reg(rd, rtv >> (rsv & 31))
            elif funct == 0x07:  # SRAV
                self.write_reg(rd, self._sra(rtv, rsv & 31))
            elif funct == 0x08:  # JR
                take_branch = True
                b_target = rsv & ~3
            elif funct == 0x09:  # JALR
                take_branch = True
                b_target = rsv & ~3
                self.write_reg(rd if rd else 31, self.pc + 4)
            elif funct == 0x0C:  # SYSCALL
                self.exception = True
            elif funct == 0x0D:  # BREAK
                self.exception = True
            elif funct == 0x10:  # MFHI
                self.write_reg(rd, self.hi)
            elif funct == 0x11:  # MTHI
                self.hi = rsv
            elif funct == 0x12:  # MFLO
                self.write_reg(rd, self.lo)
            elif funct == 0x13:  # MTLO
                self.lo = rsv
            elif funct == 0x18:  # MULT
                prod = self._sext(rsv, 32) * self._sext(rtv, 32)
                self.lo = self._u32(prod)
                self.hi = self._u32(prod >> 32)
            elif funct == 0x19:  # MULTU
                prod = rsv * rtv
                self.lo = self._u32(prod)
                self.hi = self._u32(prod >> 32)
            elif funct == 0x1A:  # DIV
                num = self._sext(rsv, 32)
                den = self._sext(rtv, 32)
                if den != 0:
                    quotient = (abs(num) // abs(den)) * (-1 if (num < 0) != (den < 0) else 1)
                    self.lo = self._u32(quotient)
                    self.hi = self._u32(num - quotient * den)
            elif funct == 0x1B:  # DIVU
                if rtv != 0:
                    self.lo = rsv // rtv
                    self.hi = rsv % rtv
            elif funct in (0x20, 0x21):  # ADD / ADDU
                self.write_reg(rd, rsv + rtv)
            elif funct in (0x22, 0x23):  # SUB / SUBU
                self.write_reg(rd, rsv - rtv)
            elif funct == 0x24:  # AND
                self.write_reg(rd, rsv & rtv)
            elif funct == 0x25:  # OR
                self.write_reg(rd, rsv | rtv)
            elif funct == 0x26:  # XOR
                self.write_reg(rd, rsv ^ rtv)
            elif funct == 0x27:  # NOR
                self.write_reg(rd, ~(rsv | rtv))
            elif funct == 0x2A:  # SLT
                self.write_reg(rd, 1 if self._sext(rsv, 32) < self._sext(rtv, 32) else 0)
            elif funct == 0x2B:  # SLTU
                self.write_reg(rd, 1 if rsv < rtv else 0)
            # unknown SPECIAL → NOP (PS1-compatible)

        # ── REGIMM ──────────────────────────────────────────────────────
        elif op == 0x01:
            signed = self._sext(rsv, 32)
            link = False
            cond = False
            if rt == 0x00:  # BLTZ
                cond = signed < 0
            elif rt == 0x01:  # BGEZ
                cond = signed >= 0
            elif rt == 0x10:  # BLTZAL
                cond = signed < 0
                link = True
            elif rt == 0x11:  # BGEZAL
                cond = signed >= 0
                link = True
            if link:
                self.write_reg(31, self.pc + 4)
            if cond:
                take_branch = True
                b_target = self._u32(self.pc + (simm << 2))

        # ── J / JAL ─────────────────────────────────────────────────────
        elif op == 0x02:  # J
            take_branch = True
            b_target = (self.pc & 0xF0000000) | (target << 2)
        elif op == 0x03:  # JAL
            take_branch = True
            b_target = (self.pc & 0xF0000000) | (target << 2)
            self.write_reg(31, self.pc + 4)

        # ── Branches ────────────────────────────────────────────────────
        elif op == 0x04:  # BEQ
            if rsv == rtv:
                take_branch = True
                b_target = self._u32(self.pc + (simm << 2))
        elif op == 0x05:  # BNE
            if rsv != rtv:
                take_branch = True
                b_target = self._u32(self.pc + (simm << 2))
        elif op == 0x06:  # BLEZ
            if self._sext(rsv, 32) <= 0:
                take_branch = True
                b_target = self._u32(self.pc + (simm << 2))
        elif op == 0x07:  # BGTZ
            if self._sext(rsv, 32) > 0:
                take_branch = True
                b_target = self._u32(self.pc + (simm << 2))

        # ── Immediate ALU ───────────────────────────────────────────────
        elif op == 0x08:  # ADDI
            self.write_reg(rt, rsv + simm)
        elif op == 0x09:  # ADDIU
            self.write_reg(rt, rsv + simm)
        elif op == 0x0A:  # SLTI
            self.write_reg(rt, 1 if self._sext(rsv, 32) < simm else 0)
        elif op == 0x0B:  # SLTIU
            self.write_reg(rt, 1 if rsv < self._u32(simm) else 0)
        elif op == 0x0C:  # ANDI
            self.write_reg(rt, rsv & imm)
        elif op == 0x0D:  # ORI
            self.write_reg(rt, rsv | imm)
        elif op == 0x0E:  # XORI
            self.write_reg(rt, rsv ^ imm)
        elif op == 0x0F:  # LUI
            self.write_reg(rt, imm << 16)

        # ── COP0 ────────────────────────────────────────────────────────
        elif op == 0x10:
            fmt = rs
            if fmt == 0x00:  # MFC0
                self.write_reg(rt, self.cop0[rd])
            elif fmt == 0x04:  # MTC0
                self.cop0[rd] = rtv
            elif fmt == 0x02:  # CFC0 (stub)
                self.write_reg(rt, self.cop0[rd])
            elif fmt == 0x06:  # CTC0 (stub)
                self.cop0[rd] = rtv
            elif fmt == 0x08:  # BC0F / BC0T — treat as never branch
                pass
            elif fmt == 0x10:  # COPz
                if funct == 0x10:  # RFE
                    sr = self.cop0[12]
                    self.cop0[12] = (sr & 0xFFFFFFF0) | ((sr >> 2) & 0x0F)
                elif funct in (0x01, 0x02, 0x06, 0x08):  # TLBR/TLBWI/TLBWR/TLBP
                    pass  # PS1 soft-float / no real TLB use in most titles

        # ── COP1 (no FPU on PS1 — NOP / ignore) ─────────────────────────
        elif op == 0x11:
            pass

        # ── COP2 GTE ────────────────────────────────────────────────────
        elif op == 0x12:
            fmt = rs
            if fmt == 0x00:  # MFC2
                self.write_reg(rt, mem.gte.data[rd])
            elif fmt == 0x02:  # CFC2
                self.write_reg(rt, mem.gte.control[rd])
            elif fmt == 0x04:  # MTC2
                mem.gte.data[rd] = rtv
            elif fmt == 0x06:  # CTC2
                mem.gte.control[rd] = rtv
            elif fmt == 0x08:  # BC2F / BC2T
                pass
            elif 0x10 <= fmt <= 0x1F:  # GTE command
                mem.gte.command(insn)

        # ── COP3 unused ─────────────────────────────────────────────────
        elif op == 0x13:
            pass

        # ── Loads ───────────────────────────────────────────────────────
        elif op == 0x20:  # LB
            addr = self._u32(rsv + simm)
            self.write_reg(rt, self._sext(mem.read8(addr), 8))
        elif op == 0x21:  # LH
            addr = self._u32(rsv + simm)
            self.write_reg(rt, self._sext(mem.read16(addr & ~1), 16))
        elif op == 0x22:  # LWL
            addr = self._u32(rsv + simm)
            self.write_reg(rt, self._lwl(mem, addr, rtv))
        elif op == 0x23:  # LW
            addr = self._u32(rsv + simm)
            self.write_reg(rt, mem.read32(addr & ~3))
        elif op == 0x24:  # LBU
            addr = self._u32(rsv + simm)
            self.write_reg(rt, mem.read8(addr))
        elif op == 0x25:  # LHU
            addr = self._u32(rsv + simm)
            self.write_reg(rt, mem.read16(addr & ~1))
        elif op == 0x26:  # LWR
            addr = self._u32(rsv + simm)
            self.write_reg(rt, self._lwr(mem, addr, rtv))

        # ── Stores ──────────────────────────────────────────────────────
        elif op == 0x28:  # SB
            addr = self._u32(rsv + simm)
            mem.write8(addr, rtv & 0xFF)
        elif op == 0x29:  # SH
            addr = self._u32(rsv + simm)
            mem.write16(addr & ~1, rtv & 0xFFFF)
        elif op == 0x2A:  # SWL
            addr = self._u32(rsv + simm)
            self._swl(mem, addr, rtv)
        elif op == 0x2B:  # SW
            addr = self._u32(rsv + simm)
            mem.write32(addr & ~3, rtv)
        elif op == 0x2E:  # SWR
            addr = self._u32(rsv + simm)
            self._swr(mem, addr, rtv)
        elif op == 0x2F:  # CACHE — R3000A; treated as NOP on PS1
            pass

        # ── Atomic / COP loads-stores (PS1: LL/SC unused; LWC2/SWC2 used) ─
        elif op == 0x30:  # LL — not on retail PS1; NOP
            pass
        elif op == 0x31:  # LWC1
            pass
        elif op == 0x32:  # LWC2
            addr = self._u32(rsv + simm)
            mem.gte.data[rt] = mem.read32(addr & ~3)
        elif op == 0x33:  # LWC3
            pass
        elif op == 0x38:  # SC
            pass
        elif op == 0x39:  # SWC1
            pass
        elif op == 0x3A:  # SWC2
            addr = self._u32(rsv + simm)
            mem.write32(addr & ~3, mem.gte.data[rt])
        elif op == 0x3B:  # SWC3
            pass

        if take_branch:
            self.branch_pending = True
            self.pending_target = b_target & ~3

        if delayed_target is not None:
            self.pc = self._u32(delayed_target)
        self.registers[0] = 0
        self.cycle_count += 1


# ── GTE / SPU / DMA / Timers / INTC / CDROM ──────────────────────────────────
class GTE:
    """RPSC1 Geometry Transformation Engine (COP2) — command dispatch."""

    def __init__(self) -> None:
        self.data = [0] * 32
        self.control = [0] * 32
        self.last_cmd = "NOP"
        self.cmd_count = 0

    def command(self, cmd: int) -> None:
        code = cmd & 0x3F
        self.last_cmd = RPSC_GTE_CMDS.get(code, f"GTE/{code:02X}")
        self.cmd_count += 1
        # Demo stubs: keep registers stable; real math TBD
        if code in (0x01, 0x30):  # RTPS / RTPT — touch SXY0
            self.data[12] = self.data[0]  # SXY0 <- VXY0 stub
        elif code == 0x12:  # MVMVA
            self.data[25] = self.data[9]  # MAC1 stub
        elif code in (0x2D, 0x2E):  # AVSZ3 / AVSZ4
            self.data[24] = (self.data[17] + self.data[18] + self.data[19]) & 0xFFFF


class SPU:
    def __init__(self) -> None:
        self.regs = [0] * 256

    def write(self, addr: int, value: int) -> None:
        self.regs[(addr >> 1) & 0xFF] = value & 0xFFFF

    def read(self, addr: int) -> int:
        if (addr & 0xFFE) == 0x1AE:  # SPUSTAT-ish
            return 0x0000
        return self.regs[(addr >> 1) & 0xFF]


class DMA:
    def __init__(self) -> None:
        self.control = 0
        self.channels = [{"madr": 0, "bcr": 0, "chcr": 0} for _ in range(7)]

    def start(self, channel: int) -> None:
        _ = channel


class Timers:
    def __init__(self) -> None:
        self.mode = [0] * 3
        self.target = [0] * 3
        self.counter = [0] * 3

    def tick(self, cycles: int) -> None:
        for i in range(3):
            self.counter[i] = (self.counter[i] + cycles) & 0xFFFF


class INTC:
    def __init__(self) -> None:
        self.i_stat = 0
        self.i_mask = 0

    def trigger(self, irq: int) -> None:
        self.i_stat |= 1 << irq

    def read_stat(self) -> int:
        return self.i_stat

    def write_stat(self, value: int) -> None:
        self.i_stat &= value

    def write_mask(self, value: int) -> None:
        self.i_mask = value & 0x7FF


class CDROM:
    """Stub CD-ROM — enough for demo; disc image loaded separately if legal."""

    def __init__(self) -> None:
        self.status = 0x18
        self.response = bytearray()
        self.image: Optional[bytearray] = None
        self.image_path: Optional[str] = None

    def load_image(self, path: str) -> int:
        with open(path, "rb") as f:
            data = f.read()
        self.image = bytearray(data)
        self.image_path = path
        return len(data)

    def write(self, addr: int, value: int) -> None:
        if (addr & 0xF) == 0:
            self.status = 0x18
            self.response = bytearray([0x02])  # stub ACK

    def read(self, addr: int) -> int:
        reg = addr & 0xF
        if reg == 0:
            return self.status
        if reg == 1 and self.response:
            return self.response.pop(0)
        return 0


class GPU:
    SCREEN_W = 320
    SCREEN_H = 240

    def __init__(self) -> None:
        self.vram = np.zeros((512, 1024, 3), dtype=np.uint8)
        self.display = np.zeros((self.SCREEN_H, self.SCREEN_W, 3), dtype=np.uint8)
        self.output = np.zeros((self.SCREEN_H, self.SCREEN_W, 3), dtype=np.uint8)
        self.black_frame = np.zeros((self.SCREEN_H, self.SCREEN_W, 3), dtype=np.uint8)
        self.gp0_buffer: list[int] = []
        self.current_cmd = 0
        self.words_needed = 1
        self.gpustat = 0x14802000

    def write_gp0(self, word: int) -> None:
        self.gp0_buffer.append(word & 0xFFFFFFFF)
        if len(self.gp0_buffer) == 1:
            self.current_cmd = (word >> 24) & 0xFF
            self._set_words_needed()
        if len(self.gp0_buffer) >= self.words_needed:
            self._execute_gp0()
            self.gp0_buffer.clear()

    def write_gp1(self, word: int) -> None:
        cmd = (word >> 24) & 0xFF
        if cmd == 0x00:
            self.display.fill(0)
        elif cmd == 0x01:
            self.gp0_buffer.clear()

    def _set_words_needed(self) -> None:
        cmd = self.current_cmd
        if 0x20 <= cmd <= 0x27:
            self.words_needed = 4 if cmd >= 0x22 else 3
        elif 0x28 <= cmd <= 0x2F:
            self.words_needed = 5
        elif 0x30 <= cmd <= 0x37:
            self.words_needed = 6
        elif 0x60 <= cmd <= 0x67:
            self.words_needed = 3
        elif cmd == 0x02:
            self.words_needed = 3
        else:
            self.words_needed = 1

    def _execute_gp0(self) -> None:
        cmd = self.current_cmd
        if 0x20 <= cmd <= 0x27:
            self._draw_mono_polygon()
        elif 0x28 <= cmd <= 0x2F:
            self._draw_textured_quad()
        elif 0x30 <= cmd <= 0x37:
            self._draw_shaded_triangle()
        elif 0x60 <= cmd <= 0x67:
            self._draw_rectangle()
        elif cmd == 0x02:
            self._fill_vram_rect()

    def _raster_triangle(self, p1, p2, p3, color, buf=None) -> None:
        if buf is None:
            buf = self.display
        pts = sorted([p1, p2, p3], key=lambda p: p[1])
        (x1, y1), (x2, y2), (x3, y3) = pts
        if y1 >= y3:
            return
        miny = max(0, y1)
        maxy = min(self.SCREEN_H - 1, y3)
        for y in range(miny, maxy + 1):
            if y < y2:
                xa = x1 + (y - y1) * (x2 - x1) // max(y2 - y1, 1)
            else:
                xa = x2 + (y - y2) * (x3 - x2) // max(y3 - y2, 1)
            xb = x1 + (y - y1) * (x3 - x1) // max(y3 - y1, 1)
            if xa > xb:
                xa, xb = xb, xa
            xa = max(0, min(xa, self.SCREEN_W - 1))
            xb = max(0, min(xb, self.SCREEN_W - 1))
            if xa <= xb:
                buf[y, xa : xb + 1] = color

    def _draw_mono_polygon(self) -> None:
        color = (
            (self.gp0_buffer[0] >> 16) & 0xFF,
            (self.gp0_buffer[0] >> 8) & 0xFF,
            self.gp0_buffer[0] & 0xFF,
        )
        pts = []
        for i in range(1, len(self.gp0_buffer)):
            x = self.gp0_buffer[i] & 0xFFFF
            y = (self.gp0_buffer[i] >> 16) & 0xFFFF
            pts.append((x & 0x3FF, y & 0x1FF))
        if len(pts) >= 3:
            self._raster_triangle(pts[0], pts[1], pts[2], color)

    def _draw_textured_quad(self) -> None:
        pts = [(80, 60), (240, 60), (240, 180), (80, 180)]
        self._raster_triangle(pts[0], pts[1], pts[2], [40, 200, 80])
        self._raster_triangle(pts[0], pts[2], pts[3], [40, 180, 70])

    def _draw_shaded_triangle(self) -> None:
        grad = np.linspace(20, 220, self.SCREEN_W, dtype=np.uint8)
        self.display[:, :, 0] = 20
        self.display[:, :, 1] = grad[None, :]
        self.display[:, :, 2] = 40

    def _draw_rectangle(self) -> None:
        color = (
            (self.gp0_buffer[0] >> 16) & 0xFF,
            (self.gp0_buffer[0] >> 8) & 0xFF,
            self.gp0_buffer[0] & 0xFF,
        )
        x = self.gp0_buffer[1] & 0xFFFF
        y = (self.gp0_buffer[1] >> 16) & 0xFFFF
        w = self.gp0_buffer[2] & 0xFFFF
        h = (self.gp0_buffer[2] >> 16) & 0xFFFF
        x2 = min(self.SCREEN_W, x + w)
        y2 = min(self.SCREEN_H, y + h)
        if x < self.SCREEN_W and y < self.SCREEN_H:
            self.display[y:y2, x:x2] = color

    def _fill_vram_rect(self) -> None:
        self.display.fill(0)

    def render_frame(self) -> np.ndarray:
        """FILES=OFF demo scene — RPSC1 CRT green triangle."""
        if getattr(self, "hardware_mode", False):
            self.output[:] = self.display
            return self.output
        self.display[:] = (8, 12, 8)
        t = time.time() * 2.5
        cx, cy = 160, 120
        pts = []
        for i in range(3):
            a = t + i * 2.094395
            pts.append((int(cx + 90 * np.cos(a)), int(cy + 90 * np.sin(a))))
        self._raster_triangle(pts[0], pts[1], pts[2], [0, 255, 65])
        # Scanline CRT feel
        self.output[:] = self.display
        self.output[::2] = (self.display[::2].astype(np.uint16) * 3 // 4).astype(np.uint8)
        return self.output


class Memory:
    def __init__(self) -> None:
        self.ram = bytearray(2 * 1024 * 1024)
        self.scratch = bytearray(1024)
        self.bios = bytearray(512 * 1024)  # empty until user loads legal BIOS
        self.bios_loaded = False
        self.cdrom = CDROM()
        self.gpu = GPU()
        self.spu = SPU()
        self.dma = DMA()
        self.timers = Timers()
        self.intc = INTC()
        self.cpu = CPU()
        self.gte = GTE()
        self._seed_demo_program()

    def _seed_demo_program(self) -> None:
        """Tiny MIPS program in KSEG0 so the CPU has real opcodes to retire (FILES=OFF)."""
        # PC starts at 0x80010000 → ram[0x10000]
        base = 0x10000
        # lui $t0, 0
        # addiu $t0, $t0, 1
        # beq $zero, $zero, -2   (spin)  — actually infinite loop with useful ops
        code = [
            0x3C080000,  # LUI  t0, 0
            0x25080001,  # ADDIU t0, t0, 1
            0x00000000,  # NOP  (SLL r0,r0,0)
            0x01084020,  # ADD  t0, t0, t0
            0x00084842,  # SRL  t1, t0, 1
            0x01285024,  # AND  t2, t1, t0
            0x01485825,  # OR   t3, t2, t0
            0x01686026,  # XOR  t4, t3, t0
            0x3C010001,  # LUI  at, 1
            0x00200821,  # ADDU at, at, $0
            0x1000FFF5,  # BEQ  zero, zero, -11  (loop)
            0x00000000,  # delay slot NOP
        ]
        for i, w in enumerate(code):
            off = base + i * 4
            self.ram[off : off + 4] = w.to_bytes(4, "little")

    def load_bios(self, path: str) -> int:
        with open(path, "rb") as f:
            data = f.read()
        n = min(len(data), len(self.bios))
        self.bios[:n] = data[:n]
        self.bios_loaded = True
        self.cpu.pc = 0xBFC00000
        self.cpu.branch_pending = False
        return n

    def _phys(self, addr: int) -> int:
        addr &= 0xFFFFFFFF
        # KSEG0/KSEG1 strip
        if 0x80000000 <= addr <= 0x9FFFFFFF:
            return addr & 0x1FFFFFFF
        if 0xA0000000 <= addr <= 0xBFFFFFFF:
            return addr & 0x1FFFFFFF
        return addr

    def read8(self, addr: int) -> int:
        p = self._phys(addr)
        if p < 0x200000:
            return self.ram[p]
        if 0x1F800000 <= p < 0x1F800400:
            return self.scratch[p - 0x1F800000]
        if 0x1FC00000 <= p < 0x1FC80000:
            return self.bios[p - 0x1FC00000]
        if 0x1F801800 <= p <= 0x1F801803:
            return self.cdrom.read(p) & 0xFF
        return 0

    def read16(self, addr: int) -> int:
        return self.read8(addr) | (self.read8(addr + 1) << 8)

    def read32(self, addr: int) -> int:
        p = self._phys(addr) & ~3
        if p < 0x200000:
            return int.from_bytes(self.ram[p : p + 4], "little")
        if 0x1FC00000 <= p < 0x1FC80000:
            i = p - 0x1FC00000
            return int.from_bytes(self.bios[i : i + 4], "little")
        if 0x1F801070 <= p <= 0x1F801077:
            return self.intc.read_stat() if (p & 4) == 0 else self.intc.i_mask
        if 0x1F801810 <= p <= 0x1F801817:
            return 0 if (p & 4) == 0 else self.gpu.gpustat
        if 0x1F801800 <= p <= 0x1F801803:
            return self.cdrom.read(p)
        if 0x1F801C00 <= p <= 0x1F801FFF:
            return self.spu.read(p)
        return 0

    def write8(self, addr: int, val: int) -> None:
        p = self._phys(addr)
        val &= 0xFF
        if p < 0x200000:
            self.ram[p] = val
        elif 0x1F800000 <= p < 0x1F800400:
            self.scratch[p - 0x1F800000] = val
        elif 0x1F801800 <= p <= 0x1F801803:
            self.cdrom.write(p, val)

    def write16(self, addr: int, val: int) -> None:
        self.write8(addr, val & 0xFF)
        self.write8(addr + 1, (val >> 8) & 0xFF)

    def write32(self, addr: int, val: int) -> None:
        p = self._phys(addr) & ~3
        val &= 0xFFFFFFFF
        if p < 0x200000:
            self.ram[p : p + 4] = val.to_bytes(4, "little")
        elif 0x1F801070 <= p <= 0x1F801073:
            self.intc.write_stat(val)
        elif 0x1F801074 <= p <= 0x1F801077:
            self.intc.write_mask(val)
        elif p == 0x1F801810:
            self.gpu.write_gp0(val)
        elif p == 0x1F801814:
            self.gpu.write_gp1(val)
        elif 0x1F801800 <= p <= 0x1F801803:
            self.cdrom.write(p, val & 0xFF)
        elif 0x1F801C00 <= p <= 0x1F801FFF:
            self.spu.write(p, val)


class Emulator:
    def __init__(self) -> None:
        self.memory = Memory()
        self.gpu = self.memory.gpu
        self.cpu = self.memory.cpu
        self.running = False
        self.disc_loaded = False
        self.bios_path: Optional[str] = None
        self.disc_path: Optional[str] = None

    def run_frame(self) -> None:
        for _ in range(25000):
            self.cpu.step(self.memory)
        self.memory.timers.tick(25000)
        self.memory.intc.trigger(0)  # VBLANK stub


# ── RPSC1-style CRT GUI ──────────────────────────────────────────────────────
class RPSC1_GUI:
    def __init__(self, root: tk.Tk, emu: Emulator) -> None:
        self.root = root
        self.emu = emu
        self.root.title(TITLE)
        self.root.configure(bg="#0a0a0a")
        # RPSC1-inspired classic desktop HUD. Controls live ABOVE the viewport,
        # so macOS/Tk window sizing cannot clip them below a 480px canvas.
        self.root.geometry("900x760")
        self.root.minsize(690, 610)

        self._photo: Optional[tk.PhotoImage] = None
        self._blank_img: Optional[tk.PhotoImage] = None
        self._canvas_image = None
        self.last_time = time.time()
        self.show_demo = False
        self._emu_thread: Optional[threading.Thread] = None

        BG = "#171b20"
        PANEL = "#252b32"
        TEXT = "#e7e9eb"
        GREEN = "#69e68a"
        self.root.configure(bg=BG)

        menubar = tk.Menu(root)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Load BIOS...", command=self.load_bios)
        file_menu.add_command(label="Load Disc...", command=self.load_disc)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        emu_menu = tk.Menu(menubar, tearoff=False)
        emu_menu.add_command(label="Run / Pause", command=self.toggle_run)
        emu_menu.add_command(label="Stop", command=self.stop_run)
        menubar.add_cascade(label="Emulation", menu=emu_menu)
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Opcode Coverage", command=self.show_rpsc)
        help_menu.add_command(label="Legal", command=self.show_legal)
        menubar.add_cascade(label="Help", menu=help_menu)
        root.configure(menu=menubar)

        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=12, pady=(9, 4))
        tk.Label(header, text="RPSC1", font=("Helvetica", 26, "bold"),
                 fg=GREEN, bg=BG).pack(side="left")
        tk.Label(header, text=f"  RPSC {VERSION}  |  PLAYSTATION EMULATOR",
                 font=("Helvetica", 11, "bold"), fg=TEXT, bg=BG).pack(side="left")
        tk.Label(header, text="FILES=OFF", font=("Courier", 10, "bold"),
                 fg=GREEN, bg=BG).pack(side="right")

        toolbar = tk.Frame(root, bg=PANEL, padx=8, pady=8)
        toolbar.pack(fill="x", padx=12, pady=(2, 5))

        def btn(parent, label, command, accent=False):
            # ttk/native Aqua buttons can ignore fg/bg; explicit Tk labels and
            # relief/border make each button readable on supported platforms.
            return tk.Button(parent, text=label, command=command,
                             font=("Helvetica", 11, "bold"),
                             bg="#000000",
                             fg="#2196ff", activebackground="#101010",
                             activeforeground="#66bbff", relief="raised", bd=2,
                             highlightthickness=1, highlightbackground="#2196ff",
                             padx=10, pady=6, cursor="hand2")

        actions = [
            ("Run / Pause", self.toggle_run, True),
            ("Stop", self.stop_run, False),
            ("Load BIOS", self.load_bios, False),
            ("Load Disc", self.load_disc, False),
            ("Opcode Info", self.show_rpsc, False),
            ("Legal", self.show_legal, False),
        ]
        # Grid stretches buttons rather than allowing a long row to overflow.
        for i, (label, callback, accent) in enumerate(actions):
            button = btn(toolbar, label, callback, accent)
            button.grid(row=i // 3, column=i % 3, sticky="ew", padx=4, pady=3)
        for column in range(3):
            toolbar.grid_columnconfigure(column, weight=1, uniform="controls")

        viewport = tk.Frame(root, bg="#080a0c", bd=2, relief="sunken")
        viewport.pack(fill="both", expand=True, padx=12, pady=(3, 5))
        self.canvas = tk.Canvas(viewport, width=640, height=480,
                                bg="black", highlightthickness=0, relief="flat")
        self.canvas.pack(expand=True)
        self.canvas.bind("<Configure>", self._center_frame)

        self.status = tk.Label(root,
            text="FILES=OFF | PRESS RUN DEMO | FPS: 0 | OP: —",
            fg=GREEN, bg=PANEL, font=("Courier", 10),
            anchor="w", padx=12, pady=8)
        self.status.pack(side="bottom", fill="x", padx=12, pady=(0, 8))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(16, self._update_display)

    def _center_frame(self, event=None) -> None:
        if self._canvas_image is not None:
            self.canvas.coords(self._canvas_image,
                               max(0, self.canvas.winfo_width() // 2 - 320),
                               max(0, self.canvas.winfo_height() // 2 - 240))

    def show_legal(self) -> None:
        messagebox.showinfo("Legal — Clean ROM", LEGAL_NOTICE)

    def show_rpsc(self) -> None:
        """KEEP THE GUI — overlay window listing imported PS1 coverage."""
        win = tk.Toplevel(self.root)
        win.title("RPSC11")
        win.configure(bg="#0a0a0a")
        win.geometry("560x640")
        txt = scrolledtext.ScrolledText(
            win, bg="#001100", fg="#00ff41", font=("Courier", 10), insertbackground="#00ff41"
        )
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("1.0", RPSC.report())
        txt.configure(state="disabled")

    def _confirm_legal(self) -> bool:
        return messagebox.askokcancel(
            "Legal ownership required",
            LEGAL_NOTICE + "\n\nContinue only if you legally own the file you will select?",
        )

    def load_bios(self) -> None:
        if not self._confirm_legal():
            return
        path = filedialog.askopenfilename(
            title="Load legally owned PS1 BIOS",
            filetypes=[("BIOS", "*.bin *.rom *.BIN *.ROM"), ("All", "*.*")],
        )
        if not path:
            return
        try:
            n = self.emu.memory.load_bios(path)
            self.emu.bios_path = path
            self.emu.gpu.hardware_mode = True
            self.status.config(text=f"BIOS loaded ({n} bytes) · {os.path.basename(path)}")
        except OSError as exc:
            messagebox.showerror("BIOS", f"Could not read BIOS:\n{exc}")

    def load_disc(self) -> None:
        if not self._confirm_legal():
            return
        path = filedialog.askopenfilename(
            title="Load legally owned PS1 disc image",
            filetypes=[
                ("PS1 Images", "*.bin *.cue *.iso *.BIN *.CUE *.ISO"),
                ("All", "*.*"),
            ],
        )
        if not path:
            return
        try:
            # Prefer .bin track if .cue selected — load raw file as demo store
            load_path = path
            if path.lower().endswith(".cue"):
                messagebox.showinfo(
                    "CUE",
                    "CUE selected. Point at the matching .bin track file for binary load,\n"
                    "or load the .bin directly. (Parser is minimal in 0.1.1.)",
                )
                return
            n = self.emu.memory.cdrom.load_image(load_path)
            self.emu.disc_loaded = True
            self.emu.disc_path = load_path
            self.status.config(
                text=f"Disc loaded ({n} bytes) · {os.path.basename(load_path)} · still demo GPU"
            )
            messagebox.showinfo(
                "Disc",
                f"Loaded {os.path.basename(load_path)} ({n} bytes).\n"
                "CPU/GPU remain in FILES=OFF demo mode until full CD boot is implemented.\n"
                "Your file stays local — nothing is uploaded.",
            )
        except OSError as exc:
            messagebox.showerror("Disc", f"Could not read image:\n{exc}")

    def toggle_run(self) -> None:
        self.emu.running = not self.emu.running
        self.show_demo = self.emu.running
        if self.emu.running:
            if self._emu_thread is None or not self._emu_thread.is_alive():
                self._emu_thread = threading.Thread(target=self._emu_loop, daemon=True)
                self._emu_thread.start()
            self.status.config(text="RUNNING · RPSC mode · FILES=OFF demo")
        else:
            self.status.config(text="PAUSED · FILES=OFF")

    def stop_run(self) -> None:
        self.emu.running = False
        self.show_demo = False
        self.status.config(text="STOPPED · FILES=OFF")

    def _emu_loop(self) -> None:
        while self.emu.running:
            start = time.monotonic()
            self.emu.run_frame()
            time.sleep(max(0, (1 / 60) - (time.monotonic() - start)))

    def _on_close(self) -> None:
        self.emu.running = False
        self.root.destroy()

    @staticmethod
    def _frame_to_photo(frame: np.ndarray) -> tk.PhotoImage:
        """Render RGB NumPy framebuffer using Tk's built-in PPM decoder (no PIL)."""
        height, width = frame.shape[:2]
        header = f"P6\n{width} {height}\n255\n".encode("ascii")
        ppm = header + np.ascontiguousarray(frame, dtype=np.uint8).tobytes()
        return tk.PhotoImage(data=ppm, format="PPM").zoom(2, 2)

    def _update_display(self) -> None:
        if not self.show_demo:
            if self._blank_img is None:
                self._blank_img = self._frame_to_photo(self.emu.gpu.black_frame)
            self._photo = self._blank_img
        else:
            self._photo = self._frame_to_photo(self.emu.gpu.render_frame())

        if self._canvas_image is None:
            self._canvas_image = self.canvas.create_image(
                0, 0, anchor=tk.NW, image=self._photo
            )
        else:
            self.canvas.itemconfigure(self._canvas_image, image=self._photo)

        self._center_frame()
        now = time.time()
        fps = int(1 / (now - self.last_time + 1e-6)) if self.show_demo else 0
        self.last_time = now
        op = self.emu.cpu.last_opcode_name
        gte = self.emu.memory.gte.last_cmd
        mode = "RUNNING" if self.show_demo else "PRESS RUN DEMO"
        bios = "BIOS:yes" if self.emu.memory.bios_loaded else "BIOS:off"
        disc = "DISC:yes" if self.emu.disc_loaded else "DISC:off"
        self.status.config(
            text=f"files=OFF · {mode} · FPS:{fps} · OP:{op} · GTE:{gte} · {bios} · {disc}"
        )
        self.root.after(16, self._update_display)


def all_opcodes_report() -> str:
    return RPSC.report()


def main() -> None:
    if sys.version_info < (3, 8):
        print("Python 3.8+ required (compatible with 3.15).", file=sys.stderr)
        sys.exit(1)
    if "--opcodes" in sys.argv or "--rpsc1" in sys.argv:
        print(RPSC.report())
        return
    root = tk.Tk()
    emu = Emulator()
    RPSC1_GUI(root, emu)  # KEEP THE GUI
    print(f"{TITLE} · files=OFF · RPSC11 · Python {sys.version.split()[0]}")
    print("Tip: python3 '#RPSC0.1.1.py' --rpsc")
    root.mainloop()


if __name__ == "__main__":
    main()
