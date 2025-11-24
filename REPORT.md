# BÁO CÁO KẾT QUẢ CRAWL TIN TỨC QUÂN SỰ

## Tổng quan
Đã crawl thành công tin tức quân sự từ 3 trang báo lớn của Việt Nam.

## Kết quả chi tiết

### 1. VNExpress - Quân sự
- **URL nguồn**: https://vnexpress.net/the-gioi/quan-su
- **Số trang crawl**: 10 trang
- **Số bài báo**: 300 bài
- **Tỷ lệ thành công**: 100% (300/300 bài)
- **Thư mục lưu**: `result/vnexpress_quansu/the-gioi_quan-su/`
- **File URLs**: `result/vnexpress_quansu/urls/the-gioi_quan-su.txt`

### 2. Dân Trí - Quân sự  
- **URL nguồn**: https://dantri.com.vn/the-gioi/quan-su
- **Số trang crawl**: 10 trang
- **Số bài báo**: 202 bài
- **Tỷ lệ thành công**: 99.5% (201/202 bài)
- **Thư mục lưu**: `result/dantri_quansu/the-gioi_quan-su/`
- **File URLs**: `result/dantri_quansu/urls/the-gioi_quan-su.txt`

### 3. VietNamNet - Quân sự
- **URL nguồn**: https://vietnamnet.vn/the-gioi/quan-su
- **Số trang crawl**: 10 trang
- **Số bài báo**: 250 bài
- **Tỷ lệ thành công**: 100% (250/250 bài)
- **Thư mục lưu**: `result/vietnamnet_quansu/the-gioi_quan-su/`
- **File URLs**: `result/vietnamnet_quansu/urls/the-gioi_quan-su.txt`

## Tổng kết
- **Tổng số bài báo đã crawl**: 751/752 bài (99.9% thành công)
- **Thời gian thực hiện**: ~6-8 phút

## Định dạng file kết quả
Mỗi file txt chứa:
1. **Tiêu đề bài báo**
2. **Ngày xuất bản** (định dạng: Thứ X, DD/MM/YYYY - HH:MM)
3. **Mô tả ngắn**
4. **Nội dung chi tiết**

## Ví dụ file đầu ra

### VNExpress
```
Oanh tạc cơ tàng hình Nga có thể chậm tiến độ vì đòn cấm vận 
Ngày xuất bản: Thứ năm, 6/11/2025, 10:24 (GMT+7)

Dự án oanh tạc cơ PAK-DA của Nga dường như đang chậm trễ...
```

### Dân Trí
```
Ukraine hé lộ địa điểm tham vấn với Mỹ về kế hoạch hòa bình 28 điểm
Ngày xuất bản: Thứ bảy, 22/11/2025 - 21:13

(Dân trí) - Ukraine xác nhận sắp thảo luận với Mỹ...
```

### VietNamNet
```
Ukraine nói Nga mất thêm tiêm kích Su-30SM ở Đảo Rắn
Ngày xuất bản: Thứ Sáu, 15/08/2025 - 08:20

Hải quân Ukraine cho biết, Nga dường như đã mất thêm...
```

## Cách sử dụng

### Chạy từng crawler riêng lẻ:
```bash
# VNExpress
python VNNewsCrawler.py --config config_vnexpress_quansu.yml

# Dân Trí
python VNNewsCrawler.py --config config_dantri_quansu.yml

# VietNamNet
python VNNewsCrawler.py --config config_vietnamnet_quansu.yml
```

### Chạy tất cả cùng lúc:
```bash
crawl_all_quansu.bat
```

## Các file cấu hình
1. `config_vnexpress_quansu.yml` - Cấu hình cho VNExpress
2. `config_dantri_quansu.yml` - Cấu hình cho Dân Trí
3. `config_vietnamnet_quansu.yml` - Cấu hình cho VietNamNet

## Tính năng đã cải tiến
✅ Hỗ trợ subcategory (quân sự) cho cả 3 trang báo
✅ Trích xuất ngày xuất bản tự động
✅ Xử lý URL động (full URL và relative path)
✅ Tạo thư mục tự động với tên an toàn (thay "/" bằng "_")
✅ Multi-threading để tăng tốc độ crawl

## Ghi chú
- Tất cả file được lưu với encoding UTF-8
- Mỗi file có định dạng nhất quán: Tiêu đề -> Ngày -> Nội dung
- Log files được lưu trong thư mục result

