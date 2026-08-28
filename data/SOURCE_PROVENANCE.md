# Nguon connectome va checkpoint

Tai lieu nay ghi nhan nguon du lieu duoc kiem tra tai ngay 28-08-2026. Du
lieu nhi phan khong duoc dua vao repository Git; nhom nghien cuu phai tai lai
va kiem tra SHA256 truoc moi chien dich.

## Nguon ma

- Repository: <https://github.com/erojasoficial-byte/fly-brain>
- Commit da kiem tra: `27cec28d5d202eb004683fb4c1a1033eec8deea0`
- License ma nguon: MIT, ban quyen Enrique Manuel Rojas Aliaga (2026).
- Commit dung trong lenh tai phai duoc ghim, khong dung nhanh `main` troi noi.

## Nguon du lieu FlyWire

- Snapshot: FlyWire FAFB v783.
- License du lieu cong khai: CC BY-NC 4.0.
- Huong dan cap phep va trich dan: <https://home.flywire.ai/guidelines>
- Nguyen tac su dung: <https://edit.flywire.ai/principles.html>
- Khi cong bo phai trich dan FlyWire va cac cong trinh ma FlyWire yeu cau;
  license MIT cua repository ma khong thay the license du lieu.

## File da kiem tra

SHA256 duoi day la cua file tai tu commit da ghim:

| File | Kich thuoc byte | SHA256 |
| --- | ---: | --- |
| `brain_body_bridge.py` | 34396 | `1ea350109fc5ffbae8baa54212fedc98267d70e2ea0c72f309572d25ba8c0a3f` |
| `code/run_pytorch.py` | 19180 | `333c09d54ee308e78916f20cc7ebca41d41e5307c7f5d7aab011a23bfc194c5b` |
| `data/2025_Completeness_783.csv` | 3327347 | `bbb847a4cc2caaa7a16349722d220c087317b946d148d4d592d94d250617a311` |
| `data/2025_Connectivity_783.parquet` | 100804642 | `efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347` |
| `data/flywire_annotations.tsv` | 32638576 | `533db093e12d8de350fd20875a967f8f74acace633ff22118eefff550d5dcbc1` |
| `data/plastic_weights.pt` | 60369156 | `d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691` |

`plastic_weights.pt` la checkpoint LFS. Script tai phai kiem tra SHA256 sau
khi tai xong; file thieu hoac sai checksum khong duoc dung.

## Trang thai

- License ma: `VERIFIED_MIT`.
- License du lieu: `VERIFIED_CC_BY_NC_4_0` cho snapshot cong khai; van phai
  trich dan va tuan dieu kien phi thuong mai.
- Tich hop source vao model moi: chua tu dong; can runtime PyTorch/FlyGym va
  kiem thu healthy truoc.
- Day la connectome LIF computational, khong phai neural model sinh hoc day du.
