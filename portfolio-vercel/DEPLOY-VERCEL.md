# Deploy chỉ Portfolio lên Vercel (từ repo crypto-trading-bot)

## Các bước trên Vercel

1. Trên trang **New Project**, phần **Import Git Repository** → bấm **Import** bên cạnh repo **`crypto-trading-bot`**.

2. Trước khi bấm **Deploy**, tìm mục **Root Directory**:
   - Bấm **Edit** (hoặc **Configure**) bên cạnh **Root Directory**.
   - Nhập: **`portfolio-vercel`**.
   - Xác nhận (Apply / Continue).

3. **Framework Preset**: chọn **Other** (hoặc **None**).

4. **Build and Output**: để mặc định (không cần build command).

5. Bấm **Deploy**.

Sau khi deploy xong, Vercel sẽ chỉ dùng nội dung trong thư mục `portfolio-vercel` (index.html + avatar.jpg), không chạy code Python hay bot. Bạn sẽ có URL dạng: `https://crypto-trading-bot-xxx.vercel.app` (hoặc tên project bạn đặt).

---

## Cập nhật portfolio sau này

1. Sửa file trong project (ví dụ `templates/portfolio.html` hoặc trực tiếp `portfolio-vercel/index.html` và `portfolio-vercel/avatar.jpg`).
2. Push lên GitHub repo `crypto-trading-bot`.
3. Vercel tự deploy lại (nếu đã bật auto-deploy). Hoặc vào Dashboard → Project → Deployments → Redeploy.
