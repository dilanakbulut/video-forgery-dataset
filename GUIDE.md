# Kendi Videon İçin Kullanım Rehberi

Bu proje tabeladaki veya reklam panosundaki içeriği perspektife uydurarak değiştirir ve değiştirilen pikseller için maske üretir. Hazır ayarlar yalnızca örnek videolara aittir. Yeni bir video eklemek için aşağıdaki yapılandırmayı kendine göre düzenlemelisin.

## 1. Kurulum

Python 3.10 veya üzeri önerilir. Proje klasöründe sanal ortam açıp bağımlılıkları kur:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 2. Videonu ekle

Kaynak videonu `originals/` klasörüne koy. Orijinal dosyanın üzerine yazma. Örnek dosya adları yerine kendi dosya adını kullan.

## 3. Pipeline yapılandırmasını düzenle

`scripts/pipeline.py` dosyasındaki `VIDEOS` sözlüğüne yeni bir video yapılandırması ekle veya mevcut örneklerden birini kopyalayıp değiştir.

Her yapılandırmada şu alanları ayarla:

- `file`: `originals/` içindeki dosya adı.
- `quad`: Tabela yüzeyinin dört köşesi, sırasıyla sol üst, sağ üst, sağ alt, sol alt; kaynak videonun piksel koordinatlarında.
- `track`: Kamera hareket ediyorsa `True`, sabitse `False`. Hareketli kamerada mevcut ORB+RANSAC izleyici başlangıç dörtgenini takip eder; çok düşük dokulu veya kıvrımlı yüzeylerde sonuçları ayrıca kontrol et.
- `mode`: `inpaint`, `inpaint_manual` veya `direct`. `inpaint` eski yazı alanını otomatik maskeleyip doldurur; `inpaint_manual` için `manual_mask` gerekir; `direct` tabela yüzeyini tamamen yeni tasarımla kaplar.
- `design`: Yeni yazı/logo katmanını ve alfa maskesini üreten fonksiyon.
- `canon`: Perspektif düzeltilmiş tasarım alanının `(genişlik, yükseklik)` ölçüsü.
- `active`: İsteğe bağlı kare aralığı `(başlangıç, bitiş)`; bitiş karesi dahil değildir. Alan yoksa tüm kareler işlenir.
- `label`: Karşılaştırma dosyalarında kullanılan kısa etiket.

Örnek köşe tanımı:

```python
quad=[(420, 180), (1180, 205), (1160, 390), (400, 365)]
```

Köşeleri kaynak videodan ekran görüntüsü çıkarıp görüntüleyicide ölç. Dört noktanın aynı düzlemsel yüzey üzerinde ve aynı sırada olduğundan emin ol. Bükülmüş/3B tabelanın farklı yüzleri tek homografiyle doğru izlenemez; yüzey başına ayrı bölge kullan.

## 4. Yeni tasarımı oluştur

Tasarım fonksiyonunun imzası `design(W, H)` olmalı ve `(overlay_bgr, alpha)` döndürmeli. `overlay_bgr`, `H×W×3` boyutlu BGR görüntü; `alpha`, `H×W` boyutlu `float32` alfa katmanı olmalı (0: şeffaf, 1: opak). Yazı, logo veya reklamı bu kanonik koordinatlarda çiz. Yazının font boyutunu ve konumunu kanonik alan içinde dene.

Eski içeriği kaldırma maskesi yetersiz kalırsa ilgili örnek yapılandırmadaki `mask_fn`/`manual_mask` yaklaşımını inceleyip videona özel maske fonksiyonu yaz. Maskeyi eski yazı ve glow’un tamamını alacak kadar geniş tut; arka planın gereksiz kısmını kapsamamaya çalış.

## 5. Önizleme ve üretim

Tek karelik önizleme üret:

```powershell
python scripts/pipeline.py --video v1 --test-frame
```

`v1` yerine `VIDEOS` sözlüğündeki anahtarı kullan. Önizleme köşeleri, yazı ölçeğini, inpainting sonucunu ve maskeyi incelemek içindir. Uygun değilse üretimden önce köşeleri, `canon` ölçülerini, tasarımı ve maske yöntemini düzelt.

Üretimi başlat:

```powershell
python scripts/pipeline.py --video v1
```

Tüm yapılandırılmış videoları üretmek için:

```powershell
python scripts/pipeline.py --video all
```

Çıktılar `manipulated/` ve `masks/` içine yazılır. Her yeni anahtara ait `file` adı benzersiz olmalı; mevcut çıktı dosyalarının üzerine yazılabileceğinden önce yedeğini al.

## 6. Doğrula ve karşılaştır

```powershell
python scripts/verify.py
python scripts/make_comparisons.py
```

Doğrulama, kaynak/manipüle/maske çözünürlüklerini ve kare sayılarını kontrol eder; her maske karesini tarayarak ikili değerleri ve gerçek manipülasyon süresini hesaplar. 4K videolarda bu tarama yavaş olabilir. Video en az 15 saniye, maske içindeki manipülasyon süresi en az 5 saniye olmalıdır. Karşılaştırma görselleri etkin maske aralığının ilk, orta ve son karelerinden oluşturulur.

Sonuçları yalnızca otomatik kontrollerle kabul etme. Üç karşılaştırma karesini ve videonun tamamını izle: eski yazı kalıntısı, titreşim, yanlış perspektif, nesne örtüşmesi, sert/halo yapan maske kenarları ve renk/parlaklık uyumsuzluğu ara. Maske sadece çıktıdaki değişen pikselleri kapsamalıdır.

## Önemli

- `originals/` içindeki kaynak videoları değiştirme.
- Tabela izleme ve inpainting sonuçları sahneye özgüdür; yeni videoda görsel kalite kontrolü şarttır.
- Büyük video dosyalarını GitHub’a eklemek yerine depoda kod ve dokümantasyon tut. Videoları gerekiyorsa Git LFS veya ayrı depolama üzerinden paylaş.
- Kullanım ve dağıtım hakkının sende olduğundan emin olduğun videoları kullan.
