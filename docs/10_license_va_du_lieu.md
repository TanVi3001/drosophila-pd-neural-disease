# License va du lieu neural

## Ma nguon

Ma `fly-brain` duoc pin tai commit `27cec28d5d202eb004683fb4c1a1033eec8deea0`
va ghi nhan license MIT trong `data/SOURCE_PROVENANCE.md`. Khong copy ma
nguon vao repository nay neu chua can thiet; script fetch giu no trong
`external/` va kiem tra hash.

## Du lieu

Connectome, completeness, annotation va checkpoint la artifact lon tu nguon
ngoai. Snapshot FlyWire v783 co dieu khoan su dung rieng, duoc ghi la
`CC BY-NC 4.0` trong provenance. License cua data khong duoc suy ra tu
license cua ma nguon.

Truoc khi dung cho paper, can:

1. Luu source commit, file version, checksum va ngay tai.
2. Doi chieu dieu khoan su dung va yeu cau citation cua FlyWire.
3. Kiem tra target neuron/edge bang annotation co provenance.
4. Khong dua checkpoint, connectome, rollout hay MP4 lon vao Git thong
   thuong; dung artifact storage va manifest.

## Trang thai hien tai

Ma va data source da duoc pin/hash kiem tra. Healthy/disease simulation chi
duoc xem la da xac nhan sau khi nhom co moi truong PyTorch CUDA + FlyGym/MuJoCo
va runner tao artifact that.
