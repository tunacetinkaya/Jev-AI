# JEV Canlı Demo 🚂

Bir Google Form'a gelen cevapları **JEV** adlı yapay zekâya okutan ve sonucu renkli bir panelde gösteren küçük bir demo projesi.

Form dolduruluyor → cevaplar Google Sheet'e düşüyor → bu proje o cevapları çekiyor → JEV her cevap için **karar** veriyor → sen de bunu ekranda canlı görüyorsun.

> Bu rehber kodlamaya yeni başlayanlar için yazıldı. Terminal ya da Python hiç kullanmadıysan bile adım adım gidersen çalışır. Takıldığın yer olursa en alttaki **Sık karşılaşılan sorunlar** bölümüne bak.

---

## İçindekiler

1. [JEV nedir?](#1-jev-nedir)
2. [Neden OpenRouter kullanıyoruz?](#2-neden-openrouter-kullanıyoruz)
3. [Projedeki dosyalar](#3-projedeki-dosyalar)
4. [Kurulum](#4-kurulum)
5. [OpenRouter API anahtarı alma](#5-openrouter-api-anahtarı-alma)
6. [Google Form ve Sheet hazırlama](#6-google-form-ve-sheet-hazırlama)
7. [`.env` dosyasını doldurma](#7-env-dosyasını-doldurma)
8. [Çalıştırma ve sayfalar](#8-çalıştırma-ve-sayfalar)
9. [Panel nasıl okunur?](#9-panel-nasıl-okunur)
10. [Kendi formunla kullanmak istersen](#10-kendi-formunla-kullanmak-istersen)
11. [Sık karşılaşılan sorunlar](#11-sık-karşılaşılan-sorunlar)
12. [Bağlantılar](#12-bağlantılar)

---

## 1. JEV nedir?

ChatGPT gibi klasik yapay zekâlar **konuşur**: sorarsın, sana bir paragraf yazar. Yazılım için bu paragrafı işlemek zordur.

**JEV** (TypeSafe şirketinin *System One* modeli) ise konuşmaz, **karar verir**. Ona şunu söylersin:

- **state:** Hakkında karar vereceği bilgi (bizde: bir form cevabı)
- **questions:** Hangi kararları istediğin

O da sana yazılımın doğrudan kullanabileceği net değerler döner. Üç tür karar var, demomuzda üçü de kullanılıyor:

| Tür | Ne yapar? | Demodaki örneği |
|---|---|---|
| `choice` | Seçeneklerden birini seçer | Kişi "Denemeye açık" mı, "Dikkatli" mi, "Mesafeli" mi? |
| `score` | Bir ölçekte puan verir | Eğitimde yapay zekâya ne kadar açık? (Düşük / Orta / Yüksek) |
| `noul` | Evet/Hayır, olasılıkla | Bu kişinin cevapları doğrulaması gerekiyor mu? |

Ayrıca JEV her kararda **ne kadar emin olduğunu** da söyler (`confidence`).

---

## 2. Neden OpenRouter kullanıyoruz?

JEV'in kendi API'sine erişmek için **whitelist'e** (onaylı kullanıcı listesine) girmek gerekiyor ve o listenin açılmasını beklemek istemedik.

Çözüm: **[OpenRouter](https://openrouter.ai)**. OpenRouter, birçok yapay zekâ modeline tek bir anahtarla (API key) ulaşmanı sağlayan bir aracı servis. JEV de OpenRouter üzerinden kullanılabiliyor, yani:

- Whitelist beklemene gerek yok.
- Sadece OpenRouter'dan bir API anahtarı almak yeterli.

Projede kullanılan ayarlar (`demo.py` içinde, değiştirmene gerek yok):

```text
Model : typesafe/jev-1.13
Adres : https://openrouter.ai/api/v1/systemone
```

> 💡 **API anahtarı (API key) nedir?** Bir servise "bu istek benden geliyor" demek için kullandığın uzun, gizli şifre. Evinin anahtarı gibi düşün: kimseyle paylaşma.

---

## 3. Projedeki dosyalar

| Dosya | Ne işe yarar? |
|---|---|
| `demo.py` | **Ana program.** Sheet'ten cevapları çeker, JEV'e sorar, paneli sunar. |
| `demo_panel.html` | **Canlı panel.** Her form cevabı bir "vagon" olarak raylara dizilir. |
| `sunum.html` | **Sunum sayfası.** JEV'in ne olduğunu, klasik yapay zekâdan farkını anlatır. |
| `requirements.txt` | Kurulması gereken Python paketlerinin listesi. |
| `.env` | **Gizli ayarlar** (API anahtarın ve Sheet kimliği). Sen oluşturacaksın. |
| `.env.example` | `.env` dosyasının boş örneği. Kopyalayıp kullanacaksın. |

---

## 4. Kurulum

### Önce bilgisayarında olması gerekenler

- **Python 3.10 veya daha yenisi.** Kontrol etmek için terminali aç ve yaz:

  ```bash
  python3 --version
  ```

  Sürüm görüyorsan tamam. Yoksa [python.org/downloads](https://www.python.org/downloads/) adresinden indir.

> **Terminal nasıl açılır?**
> - **Mac:** Cmd + Boşluk → "Terminal" yaz → Enter
> - **Windows:** Başlat → "PowerShell" yaz → Enter

### Adım adım

**1) Proje klasörüne gir.**

```bash
cd jev-ai
```

(Klasörü başka yere indirdiysen yolunu ona göre yaz.)

**2) Sanal ortam (virtual environment) oluştur.** Bu, projenin paketlerini bilgisayarının geri kalanından ayrı tutan küçük bir kutudur.

```bash
python3 -m venv .venv
```

**3) Sanal ortamı aç.**

Mac / Linux:

```bash
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

Başarılı olursa satırın başında `(.venv)` yazar.

**4) Gerekli paketleri kur.**

```bash
pip install -r requirements.txt
```

Kurulanlar: `fastapi` ve `uvicorn` (siteyi çalıştırır), `python-dotenv` (`.env` dosyasını okur), `requests` (internetten veri çeker).

**5) `.env` dosyasını oluştur.**

Mac / Linux:

```bash
cp .env.example .env
```

Windows (PowerShell):

```powershell
copy .env.example .env
```

Bu dosyayı **birazdan** dolduracağız. Önce anahtarı ve formu hazırlayalım.

---

## 5. OpenRouter API anahtarı alma

🎥 **Video anlatım:** [OpenRouter'dan API key nasıl alınır?](https://www.youtube.com/watch?v=1dYRajXZUYs)

Videoyu izleyebilir ya da aşağıdaki adımları takip edebilirsin:

1. [openrouter.ai](https://openrouter.ai) adresine git ve **Sign in** ile hesap aç (Google ile girebilirsin).
2. Sağ üstteki profil menüsünden **Keys** (API Keys) sayfasına git: [openrouter.ai/keys](https://openrouter.ai/keys)
3. **Create Key** butonuna bas, anahtara bir isim ver (mesela `jev-demo`).
4. Çıkan anahtarı **hemen kopyala.** Genelde `sk-or-v1-...` diye başlar. Güvenlik için bir daha tamamını göstermez.
5. Anahtarı `.env` dosyandaki `AI_OPEN_ROUTER_API_KEY=` satırına yapıştıracaksın (bkz. [Bölüm 7](#7-env-dosyasını-doldurma)).

> ⚠️ **Dikkat:**
> - API anahtarını kimseyle paylaşma, ekran görüntüsünde gösterme, GitHub'a yükleme.
> - OpenRouter'da kullanım kredi ile çalışabilir; hesabında kredi yoksa istekler hata verebilir. Kredi durumunu [openrouter.ai/credits](https://openrouter.ai/credits) sayfasından kontrol et. (Kuralları zamanla değişebilir, güncel durum için OpenRouter'a bak.)
> - Bu demo her form cevabı için JEV'e bir istek atar; birkaç düzine cevap çok küçük bir maliyettir.

---

## 6. Google Form ve Sheet hazırlama

Kendi formunu kurmak istersen aşağıdakileri **birebir** yap. Program, sütunları **soru başlığına bakarak** tanıyor, bu yüzden başlıkların aynı olması önemli.

### 6.1 Formu oluştur

1. [forms.google.com](https://forms.google.com) → **Boş form**
2. Aşağıdaki **4 soruyu** bu sırayla ve bu başlıklarla ekle:

| # | Soru başlığı (aynen yaz) | Soru türü |
|---|---|---|
| 1 | `Yapay zekâyı üniversitede en çok hangi amaçla kullanırsın?` | Kısa yanıt ya da çoktan seçmeli |
| 2 | `Yapay zekâdan aldığın cevaba ne kadar güvenirsin?` | **Doğrusal ölçek**, 1–5 |
| 3 | `Yapay zekânın eğitimde gerçekten faydalı olması için ne yapması gerekir?` | Paragraf |
| 4 | `Yapay zekâ kullanırken en büyük endişen nedir?` | Paragraf |

> ⚠️ **Çok önemli:** Başlıklardaki `â` harfi ("zekâ", "zekâyı", "zekâdan", "zekânın") **şapkalı** olmalı. Şapkasız "zekayı" yazarsan program sütunu tanımaz. Büyük/küçük harf ve baştaki/sondaki boşluk fark etmez, ama harfler aynı olmalı.
>
> Soruları kopyala-yapıştır yapmak en güvenlisi.

3. Üstteki **Yanıtlar** sekmesine geç.

### 6.2 Cevapları Google Sheet'e bağla

1. **Yanıtlar** sekmesinde yeşil **Sheets'e bağla** (Link to Sheets) butonuna bas.
2. **Yeni e-tablo oluştur** seç → **Oluştur**.
3. Sheet açılır. Artık her form cevabı buraya yeni bir satır olarak düşecek.

### 6.3 Sheet'i program okuyabilsin diye paylaş

Program Sheet'i internetten okuyor. Bu yüzden herkesin **görüntüleyebileceği** şekilde paylaşmalısın:

1. Sheet'te sağ üstten **Paylaş** butonuna bas.
2. **Genel erişim** kısmını **"Bağlantıya sahip olan herkes"** yap.
3. Yetkiyi **Görüntüleyen** (Viewer) olarak bırak. *Düzenleyen yapma!*
4. **Bitti**.

> 🔒 Sheet'i bağlantısı olan herkes **görüntüleyebilir**. Formda isim, telefon gibi kişisel bilgi **sorma**. Bu demo anonim cevaplar için tasarlandı.

### 6.4 Sheet kimliğini (SHEET_ID) bul

Sheet'in adres çubuğundaki linke bak:

```text
https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890/edit#gid=0
                                       └─────────── SHEET_ID ───────────┘
```

`/d/` ile `/edit` arasındaki uzun yazı senin **SHEET_ID**'n. Onu kopyala.

> Program, Sheet'in **ilk sekmesini** okur. Cevap sekmesini sürükleyip en başa koymayı unutma. (Form bağlayınca zaten ilk sekme o olur.)

---

## 7. `.env` dosyasını doldurma

`.env` dosyasını bir metin editöründe aç (VS Code, Not Defteri vs.) ve şöyle doldur:

```env
AI_OPEN_ROUTER_API_KEY=sk-or-v1-buraya-kendi-anahtarini-yapistir
SHEET_ID=buraya-sheet-kimligini-yapistir
```

Kurallar:

- `=` işaretinin iki yanında **boşluk bırakma.**
- Tırnak işareti **koyma.**
- Bu dosyayı kimseye gönderme. Sınıfla projeyi paylaşırken `.env` dosyasını **dahil etme**, sadece `.env.example` kalsın.

---

## 8. Çalıştırma ve sayfalar

Terminalde, proje klasöründe ve sanal ortam açıkken (satır başında `(.venv)` olmalı):

```bash
python demo.py
```

Şu yazıyı görürsen çalışıyordur:

```text
Panel: http://127.0.0.1:8001
```

Şimdi tarayıcıdan bu adreslere gidebilirsin:

| Adres | Ne açılır? |
|---|---|
| [http://127.0.0.1:8001/](http://127.0.0.1:8001/) | **Canlı panel.** Form cevaplarının JEV tarafından işlendiği asıl demo. |
| [http://127.0.0.1:8001/?demo](http://127.0.0.1:8001/?demo) | **Örnek veriyle panel.** Form, Sheet ya da API anahtarı olmadan paneli denemek için. İlk önce bunu aç! |
| [http://127.0.0.1:8001/sunum](http://127.0.0.1:8001/sunum) | **Sunum sayfası.** JEV'in ne olduğunu ve klasik yapay zekâdan farkını anlatan kaydırmalı sayfa. |
| [http://127.0.0.1:8001/api/cevaplar](http://127.0.0.1:8001/api/cevaplar) | Sheet'teki cevapları ham veri (JSON) olarak gösterir. Bağlantıyı test etmek için güzel. |

Programı **durdurmak** için terminalde `Ctrl + C`'ye bas.

### Demo sırasında akış

1. Sınıfa formun linkini gönder, herkes doldursun.
2. Panelde **Cevapları çek** butonuna bas (ya da **Canlı** düğmesiyle her 7 saniyede otomatik yenilet).
3. Yeni cevaplar JEV'e gider ve vagonlar raylara dizilir.
4. Yeni cevap geldikçe butona tekrar bas. Daha önce analiz edilenler tekrar sorulmaz (önbellekte tutulur), böylece hem hızlı hem ucuz.

> 📝 Önbellek program kapanınca silinir. Yeniden başlatırsan tüm cevaplar tekrar JEV'e gider.

---

## 9. Panel nasıl okunur?

Panel bir **manevra sahası** gibi kurgulandı:

- **Her form cevabı bir vagon.**
- **Ray = JEV'in `choice` kararı.** Kişi hangi profile uyuyorsa o raya gider (Denemeye açık, Faydacı, Dikkatli, Mesafeli, Diğer).
- **Vagonun ray üzerindeki konumu = `score` kararı.** Eğitimde yapay zekâya ne kadar açıksa o kadar ileri gider.
- **Doğrulama işareti = `noul` kararı.** Kişi yanlış bilgi/kaynak konusunda endişeliyse işaretlenir (olasılık %70 ve üzeriyse "evet").
- **JEV'in güveni (confidence):** Seçtiği cevaptan ne kadar emin olduğu. **%60'ın altı "belirsiz"** sayılır.
- Bir vagona tıklarsan JEV'e giden `state` verisini ve kararın detayını görürsün.

> ⚠️ Etiketler kişi hakkında hüküm değildir. Sadece o anki form cevaplarına bakan bir tahmindir. Gerçek hayatta bir insan hakkında karar vermek için kullanma.

---

## 10. Kendi formunla kullanmak istersen

**Soru metinlerini** değiştirmek istersen iki yol var:

**Kolay yol:** Formdaki başlıkları Bölüm 6.1'deki gibi tut. Hiçbir koda dokunma.

**Kendi sorularını yazmak:** `demo.py` dosyasında `HEADER_FIELDS` bölümünü bul. Orada sol taraf **form sorusunun küçük harfli başlığı**, sağ taraf **programın içindeki adı**:

```python
HEADER_FIELDS = {
    "zaman damgası": "timestamp",
    "yapay zekâyı üniversitede en çok hangi amaçla kullanırsın?": "ai_usage_area",
    ...
}
```

Sol tarafı kendi sorunla değiştir (küçük harfle yaz). Sağ taraftaki adlara dokunma.

**JEV'e sorulan soruları** değiştirmek için aynı dosyada `QUESTIONS` bölümüne bak. `profile`, `adoption_readiness` ve `needs_verification` adlı üç karar orada tanımlı. Seçenekleri ve açıklamaları kendi konuna göre değiştirebilirsin. Ne kadar net yazarsan JEV o kadar iyi karar verir.

---

## 11. Sık karşılaşılan sorunlar

| Gördüğün hata | Muhtemel sebep ve çözüm |
|---|---|
| `command not found: python` | `python3` yaz. Hâlâ yoksa Python'u kur. |
| `ModuleNotFoundError: No module named 'fastapi'` | Sanal ortam açık değil ya da paketler kurulmadı. Bölüm 4, 3. ve 4. adımları tekrarla. |
| `SHEET_ID ortam değişkeni tanımlı değil` | `.env` dosyası yok, yanlış yerde ya da `SHEET_ID` boş. |
| `AI_OPEN_ROUTER_API_KEY ortam değişkeni tanımlı değil` | `.env` içinde API anahtarı boş ya da yanlış yazılmış. |
| `Sheet okunamadı (404)` / `(403)` | SHEET_ID yanlış ya da paylaşım "Bağlantıya sahip olan herkes" değil. Bölüm 6.3. |
| `Sheet CSV yerine bir sayfa döndü` | Paylaşım ayarı kapalı. Bölüm 6.3. |
| `Beklenen sütunlar yok` | Form soru başlıkları farklı. Özellikle **â** harfine dikkat. Bölüm 6.1. |
| `JEV yanıt vermedi (401)` | API anahtarı yanlış ya da silinmiş. OpenRouter'dan yenisini al. |
| `JEV yanıt vermedi (402)` | OpenRouter hesabında kredi yok. [openrouter.ai/credits](https://openrouter.ai/credits) |
| `JEV yanıt vermedi (404)` | Model adı ya da adres değişmiş olabilir. OpenRouter'da modelin güncel adını kontrol et. |
| `Address already in use` | Port 8001 başka bir şey tarafından kullanılıyor. Önceki `python demo.py` penceresini `Ctrl + C` ile kapat. |
| Panel boş görünüyor | Sheet'te henüz cevap yok. Formu bir kez kendin doldur. Ya da `/?demo` adresini aç. |

Hâlâ çözemediysen terminaldeki **kırmızı hata yazısını** kopyalayıp öğretmenine ya da bir yapay zekâ asistanına yapıştırıp "bu hata ne demek?" diye sor. Hata mesajları çoğu zaman çözümü söyler.

---

## 12. Bağlantılar

**JEV / TypeSafe**

- [TypeSafe: JEV ve System One modelleri tanıtım yazısı](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- [TypeSafe ana sayfa](https://typesafe.ai/)
- [TypeSafe API dokümantasyonu](https://api.typesafe.ai/docs)
- [TypeSafe OpenAPI şeması](https://api.typesafe.ai/openapi.json)
- [JEV AI geliştirici rehberi (GitHub)](https://github.com/jev-ai/jev-api)

**OpenRouter**

- [OpenRouter](https://openrouter.ai)
- [API anahtarı oluşturma sayfası](https://openrouter.ai/keys)
- 🎥 [Video: OpenRouter'dan API key nasıl alınır?](https://www.youtube.com/watch?v=1dYRajXZUYs)

**Kullandığımız araçlar**

- [Python](https://www.python.org/downloads/)
- [Google Forms](https://forms.google.com)
- [FastAPI](https://fastapi.tiangolo.com/)

> Model adları, fiyatlar ve erişim yöntemleri erken erişim döneminde değişebilir. Bir şey çalışmazsa önce yukarıdaki resmî dokümanlara bak.

---

Hazırlayan: Yapay Zekâ Operatörlüğü sınıfı için 🚂
