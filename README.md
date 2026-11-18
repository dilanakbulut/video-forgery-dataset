# Video Forgery Dataset: Billboard and Signage Manipulation

Bu veri kümesi, beş kaynak videonun orijinallerini koruyarak oluşturulan manipüle video ve piksel düzeyinde ground-truth maske çiftlerini içerir.

## Yapı

- `originals/`: Değiştirilmemiş kaynak videolar.
- `manipulated/`: Yeniden kodlanmış manipülasyon çıktıları.
- `masks/`: FFV1 ile kayıpsız saklanan, 0/255 değerli ikili maskeler.
- `comparisons/`: Aralık başlangıcı, ortası ve sonundan orijinal / manipüle / maske karşılaştırmaları.
- `scripts/`: Üretim, doğrulama ve karşılaştırma kodları.

Proje kökünde duran aynı isimli MP4 dosyaları orijinal kopyalardır; üretim betiği yalnızca `originals/` dizinini okur.

## Videolar

| Video | Değiştirilen içerik | Yeni içerik | İşlenen aralık | Süre |
|---|---|---|---|---:|
| v1 | Büfe tabelası ve içecek amblemi | CAN BÜFE / Fizz | Tüm video | 17.76 sn |
| v2 | LIDL mağaza logosu | NOVA | Tüm video | 26.53 sn |
| v3 | NHAT LINH ve BIA HA NOI yazıları | THANH TAM ve BIA SAO MAI | Kare 320–514 | 7.80 sn |
| v4 | FOSTERS neon tabelası | PARKERS | Tüm video | 15.31 sn |
| v5 | Piccadilly LED reklamı | VIVA / Live Without Limits | Tüm video | 22.89 sn |

Tüm kaynak videolar en az 15 saniye; maske ile ölçülen gerçek manipülasyon süresi en az 5 saniye olmalıdır.

## Üretim ve doğrulama

```powershell
python scripts/pipeline.py --video all
python scripts/verify.py
python scripts/make_comparisons.py
```

Tek video işlemek için `--video v1`–`--video v5` kullanılır. Her maske karesi sıralı olarak taranır; ikili değerler, kare sayısı, çözünürlük ve FPS denetlenir. Manipülasyon süresi, yapılandırılmış zaman aralığından değil maske içindeki sıfır olmayan karelerden hesaplanır. Karşılaştırma betiği bu maskenin ilk, orta ve son etkin karelerini üretir.

Arkadaşlarının kendi videolarını ekleme adımları için [GUIDE.md](GUIDE.md) dosyasına bakın. Python bağımlılıkları `requirements.txt` içinde listelenmiştir. Büyük MP4/MKV videolar `.gitignore` ile Git takibinin dışında tutulur; kod ve rehber dosyaları paylaşılır.

## Yöntem

Kamera hareketinin bulunduğu v1 ve v4 için tabela yüzeyindeki ORB özellikleri referans kareye karşı eşleştirilir; RANSAC homografisiyle yüzey dörtgeni kareler boyunca izlenir. v4 köşeleri tracker'ın referans karesi olan frame 0 üzerinde ölçülür. Diğer videolarda sabit yüzey koordinatları kullanılır. Yazı ve logolar perspektifi düzeltilmiş tabela koordinatlarında oluşturulur ve geri taşınır. v1/v2 eski içeriği renk/kontrast temelli maske ve OpenCV Telea inpainting ile temizler. v3, kadrajın kestiği iki tonlu tabela bandını yeniden kurar; v4 eski neon yazıyı tamamen kapatmak için tabela yüzünü PARKERS neon tasarımıyla yeniden çizer; v5 LED ekranı yeni reklam tasarımıyla değiştirir.

Ground-truth maskesi, kompozit işlemin gerçekten değiştirdiği piksellerden oluşturulur ve bulanık kompozisyon kenarlarını da içerir. Maske dışındaki pikseller kaynak kareden alınır. Manipüle video H.264, maske FFV1 ile yazılır.

## Görsel kalite notu

v4 tabelası düz olmayan, öne çıkan kıvrımlı bir neon yüzeydir. Tek bir homografi yaklaşık yüzey eşlemesi sağlar; perspektif/geometri ve neon temizliği karşılaştırma görsellerinde ayrıca incelenmelidir. Bu nedenle bu veri kümesi araştırma kullanımından önce insan görsel kalite kontrolü gerektirir.

Bu revizyon turunda beş manipüle video ve maske yeniden üretildi. Beş maskenin bütün kareleri ikili değer, kare sayısı ve etkin manipülasyon aralığı açısından tarandı; tüm teknik gereksinimler geçti. `verify.py` bütün maskeleri kare kare tarar; bu işlem 4K FFV1 maskelerinde zaman alabilir.

## Araçlar

Python, OpenCV, NumPy ve `imageio-ffmpeg` ile sağlanan FFmpeg kullanılır. Pipeline yollarını script dosyasının konumuna göre çözer; çalışma dizinine bağlı değildir.
