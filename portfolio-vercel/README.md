# Portfolio — Deploy lên Vercel

Chỉ chứa trang Portfolio (static HTML + ảnh). Deploy lên Vercel để có URL public.

## Cách deploy

### Cách 1: Deploy qua Vercel Dashboard (khuyến nghị)

1. Đăng nhập [vercel.com](https://vercel.com) (dùng GitHub).
2. **Add New** → **Project**.
3. **Import Git Repository**:  
   - Nếu folder `portfolio-vercel` nằm trong repo riêng: chọn repo đó, **Root Directory** đặt là `./` (hoặc folder chứa `index.html`).  
   - Nếu chưa có repo: tạo repo mới chỉ chứa nội dung thư mục này (chỉ `index.html`, `avatar.jpg`, `vercel.json`, `README.md`), rồi import repo đó. **Root Directory** để trống hoặc `./`.
4. **Framework Preset**: chọn **Other** (hoặc **No framework**).
5. **Build and Output**: để mặc định (không cần build).
6. Bấm **Deploy**. Xong sẽ có URL dạng `https://tên-project.vercel.app`.

### Cách 2: Deploy bằng Vercel CLI

1. Cài Vercel CLI (nếu chưa có):
   ```bash
   npm i -g vercel
   ```
2. Mở terminal trong thư mục **portfolio-vercel** (chứa `index.html` và `avatar.jpg`):
   ```bash
   cd portfolio-vercel
   vercel
   ```
3. Lần đầu: đăng nhập, chọn scope, tên project. Sau đó Vercel sẽ build và cho bạn URL.

### Cập nhật nội dung

- Sửa file trong `templates/portfolio.html` (project chính), rồi copy nội dung sang `portfolio-vercel/index.html` (đổi `src="/static/avatar.jpg"` thành `src="./avatar.jpg"`).
- Hoặc sửa trực tiếp `portfolio-vercel/index.html` và `portfolio-vercel/avatar.jpg`.
- Push lên Git (nếu dùng GitHub) hoặc chạy lại `vercel --prod` trong thư mục `portfolio-vercel` để deploy bản mới.
