"""Prints duration / peak dBFS / RMS dBFS / spectral centroid for every decoded source: python3 -I catalog.py [pack-prefix]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import dsp
pre = sys.argv[1] if len(sys.argv) > 1 else ''
for pack in sorted(os.listdir(dsp.SRC)):
    if not pack.startswith(pre):
        continue
    for n in dsp.listpack(pack):
        x = dsp.load(pack, n)
        if len(x) < 10:
            continue
        sp = np.abs(np.fft.rfft(x[:2 ** 17]))
        fr = np.fft.rfftfreq(min(len(x), 2 ** 17), 1 / dsp.SR)
        cen = (sp * fr).sum() / (sp.sum() + 1e-9)
        rms = np.sqrt(np.mean(x ** 2))
        print(f'{pack}/{n}\t{len(x)/dsp.SR:.2f}s\tpk{20*np.log10(dsp.peak(x)):.0f}\trms{20*np.log10(rms+1e-9):.0f}\tc{cen:.0f}')
