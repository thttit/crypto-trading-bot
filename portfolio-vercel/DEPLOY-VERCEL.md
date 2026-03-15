# Deploy chỉ Portfolio lên Vercel

## Bước 1: Đảm bảo folder `portfolio-vercel` có trên GitHub

1. Mở repo **crypto-trading-bot** trên GitHub: https://github.com/thttit/crypto-trading-bot  
2. Kiểm tra xem có thư mục **portfolio-vercel** (bên cạnh `static`, `templates`) không.

**Nếu chưa thấy** → push từ máy local:

```bash
cd c:\Users\khanh.mai\crypto-trading-bot
git add portfolio-vercel
git status
git commit -m "Add portfolio-vercel for Vercel deploy"
git push origin main
```

Sau đó refresh lại trang repo trên GitHub.

---

## Bước 2: Deploy trên Vercel

### Cách A: Chọn Root Directory (khi đã có `portfolio-vercel` trên GitHub)

1. **Import** repo **crypto-trading-bot**.
2. Ở bước **Configure Project**, mục **Root Directory** → bấm **Edit**.
3. Nếu trong list có **portfolio-vercel** → chọn **portfolio-vercel** → **Continue**.
4. Nếu **không có** trong list nhưng bạn chắc đã push:
   - Thử **Cancel** rồi **Import** lại repo (để Vercel refresh).
   - Hoặc thử nhập tay **`portfolio-vercel`** nếu có ô nhập path.
5. **Framework Preset**: **Other**. Bấm **Deploy**.

### Cách B: Tạo repo riêng chỉ cho Portfolio (chắc chắn deploy đúng)

Khi không chọn được Root Directory, dùng repo chỉ chứa nội dung portfolio:

1. Trên GitHub: **New repository** → tên ví dụ **portfolio** (hoặc **thy-portfolio**) → Public → Create.
2. Trên máy, tạo bản copy và push:

```bash
cd c:\Users\khanh.mai\crypto-trading-bot\portfolio-vercel
git init
git add .
git commit -m "Portfolio static site"
git branch -M main
git remote add origin https://github.com/thttit/portfolio.git
git push -u origin main
```

(Thay `thttit/portfolio` bằng tên repo bạn vừa tạo.)

3. Trên Vercel: **New Project** → **Import** repo **portfolio** vừa tạo.  
   Không cần chỉnh Root Directory → **Deploy**.

Sau khi deploy xong, bạn sẽ có URL dạng `https://portfolio-xxx.vercel.app`.
