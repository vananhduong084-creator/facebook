# FB Reels Watcher

Python script chạy trên GitHub Actions mỗi 5 phút.
Phát hiện Reel mới trên 1 Fanpage và tự comment 1 đoạn text + link cố định (lấy từ `default-comment.txt`).

## Cấu trúc

```
.
├── watcher.py                          # Logic chính
├── default-comment.txt                 # Nội dung comment + link
├── requirements.txt                    # Python deps
└── .github/workflows/watcher.yml       # Cron schedule (mỗi 5 phút)
```

## Setup

### 1. Tạo repo trên GitHub

- Push toàn bộ folder này lên 1 repo
- Repo có thể **public** (miễn phí Actions không giới hạn) hoặc **private** (2000 phút/tháng, đủ dùng ở 5-phút/lần)

### 2. Thêm Secrets

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Thêm:
- `FB_PAGE_ID` = Page ID (số 15-16 chữ số)
- `FB_PAGE_ACCESS_TOKEN` = never-expire Page Access Token

### 3. Sửa cấu hình workflow

Mở `.github/workflows/watcher.yml`, sửa biến `WATCHER_START_ISO` thành thời điểm hiện tại (UTC). Reels tạo TRƯỚC mốc này sẽ bị bỏ qua.

### 4. Enable Actions

Repo → **Settings** → **Actions** → **General** → chọn **"Allow all actions and reusable workflows"** → Save

Workflow sẽ tự chạy mỗi 5 phút. Có thể trigger thủ công ở **Actions** → **FB Reels Watcher** → **Run workflow**.

## Đổi nội dung comment

Sửa file `default-comment.txt`, commit, push. Workflow lần sau dùng nội dung mới.

## Đổi tần suất check

Sửa cron expression trong `.github/workflows/watcher.yml`:

| Cron | Tần suất |
|---|---|
| `*/5 * * * *` | Mỗi 5 phút (mặc định) |
| `*/10 * * * *` | Mỗi 10 phút |
| `0 * * * *` | Đầu mỗi giờ |
| `0,30 * * * *` | Giờ tròn + giờ rưỡi |

GitHub minimum interval: 5 phút. Có thể delay 5-15 phút khi server tải cao.

## Đổi Page

Đổi `FB_PAGE_ID` trong Secrets. Đảm bảo `FB_PAGE_ACCESS_TOKEN` có quyền trên Page đó.

## Tắt tạm

Repo → **Settings** → **Actions** → **General** → **Disable actions**.
Hoặc xoá workflow file.
