import zipfile

import numpy as np
import pytest

from resonance import accel


def _samples(fs=100.0, f=20.0, seconds=10.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.cumsum(rng.uniform(0.9, 1.1, int(fs * seconds))) / fs  # phone sensors jitter
    x = 0.05 * np.sin(2 * np.pi * f * t) + 0.005 * rng.standard_normal(t.size)
    y = 0.02 * np.sin(2 * np.pi * f * t + 1.0) + 0.005 * rng.standard_normal(t.size)
    z = 0.01 * rng.standard_normal(t.size) + 0.3  # residual offset
    return t, np.stack([x, y, z], 1)


HEADER = ["Time (s)", "Linear Acceleration x (m/s^2)", "Linear Acceleration y (m/s^2)", "Linear Acceleration z (m/s^2)", "Absolute acceleration (m/s^2)"]


def _write_csv(path, t, xyz, delim=",", decimal_comma=False):
    absval = np.linalg.norm(xyz, axis=1)
    lines = [delim.join(f'"{h}"' for h in HEADER)]
    for row in np.column_stack([t, xyz, absval]):
        vals = [f"{v:.9E}" for v in row]
        if decimal_comma:
            vals = [v.replace(".", ",") for v in vals]
        lines.append(delim.join(vals))
    path.write_text("\n".join(lines) + "\n")
    return path


@pytest.mark.parametrize("delim,decimal_comma", [(",", False), (";", True), ("\t", True)])
def test_loads_all_phyphox_csv_flavours(tmp_path, delim, decimal_comma):
    t, xyz = _samples()
    rec = accel.load_phyphox(_write_csv(tmp_path / "Raw Data.csv", t, xyz, delim, decimal_comma))
    assert rec.xyz.shape == (t.size, 3)
    assert rec.fs == pytest.approx(100.0, rel=0.05)
    assert np.allclose(rec.xyz[:, 0], xyz[:, 0], atol=1e-6)


def test_loads_phyphox_zip_export(tmp_path):
    t, xyz = _samples()
    csv_path = _write_csv(tmp_path / "Raw Data.csv", t, xyz)
    zpath = tmp_path / "Acceleration without g 2026-10-27.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("meta/device.csv", '"property","value"\n"deviceModel","Pixel"\n')
        z.write(csv_path, "Raw Data.csv")
    rec = accel.load_phyphox(zpath)
    assert rec.source.endswith("Raw Data.csv")
    assert rec.t.size == t.size


def test_compare_agrees_with_matching_video_frequency(tmp_path):
    t, xyz = _samples(f=20.0)
    rec = accel.load_phyphox(_write_csv(tmp_path / "a.csv", t, xyz))
    cmp = accel.compare(20.05, rec)
    assert cmp.verifiable
    assert cmp.accel_dominant.freq_hz == pytest.approx(20.0, abs=0.1)
    assert cmp.percent_error < 1.0


def test_compare_refuses_above_accelerometer_nyquist(tmp_path):
    t, xyz = _samples(fs=100.0, f=20.0)
    rec = accel.load_phyphox(_write_csv(tmp_path / "a.csv", t, xyz))
    cmp = accel.compare(60.0, rec)  # e.g. blade-pass frequency on a ~100 Hz iPhone sensor
    assert not cmp.verifiable
    assert "Nyquist" in cmp.note


def test_rejects_csv_without_acceleration_columns(tmp_path):
    p = tmp_path / "gyro.csv"
    p.write_text('"Time (s)","Gyroscope x (rad/s)"\n0,1\n0.01,2\n0.02,3\n')
    with pytest.raises(accel.AccelError):
        accel.load_phyphox(p)
