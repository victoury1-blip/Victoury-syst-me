# Victoury-syst-me — Meta Ads Daily Budget Optimizer

سكريبت كيقرا أداء الحملات ديالك (Meta / Facebook Ads) كل يوم أوتوماتيك، وكيبدل الميزانية اليومية حسب قواعد أنت اللي كتحددها (CPA المستهدف، نسبة الزيادة/النقصان، حد الوقف...). خدام عبر GitHub Actions، ماخصكش سيرفر ديالك.

## شنو كيدير

كل يوم (عبر GitHub Actions):
1. كيجمع بيانات الأداء ديال آخر `lookback_days` أيام لكل Ad Set نشيط (Spend, Résultats/Purchases)
2. كيحسب الـ CPA (تكلفة كل نتيجة)
3. كيقرر:
   - **CPA <= الهدف** → يزيد الميزانية بـ `increase_pct` (افتراضي 20%)
   - **CPA > الهدف بشوية** → ينقص الميزانية بـ `decrease_pct`
   - **CPA > الهدف بزاف** (`pause_cpa_multiplier`) → يوقف الـ Ad Set
   - **ماكافيش نتائج كافية** → مايبدلش والو، غير كيسجل
4. عندو **Cooldown** (`min_days_between_changes`) باش مايبدلش الميزانية كل يوم بلا ما يخلي الخوارزمية ديال Meta تتأقلم
5. عندو **Dry Run** (`dry_run: true` فـ `config.yaml`) — كيقرا وكيقترح غير بلا ما يبدل والو فالحقيقة، حتى تتأكد اللي القواعد صافية
6. كيكتب تقرير يومي (GitHub Actions Summary) + تنبيه Telegram اختياري

## تقرير تحليلي شامل على كل الحملات (Campaign Analytics Report)

بزيادة على تحسين الميزانية، كاين سكريبت `meta_ads/campaign_report.py` كيدير جرد شامل على **جميع الحملات** فالحساب ديالك (ماشي غير الـ Ad Sets النشيطة)، وكيعطيك جدول: Spend, Impressions, Clicks, CTR, CPC, Résultats, CPA, ROAS — لكل حملة، مرتبة من الأكثر صرف للأقل.

**كيفاش تشغلو:**
- من GitHub: **Actions → Meta Ads Campaign Analytics Report → Run workflow** (بوطون يدوي، وقتما بغيتي)
- كيخدم أوتوماتيك تانية كل نهار الإثنين (اختياري، تقدر تبدلو أو تحيدو من `.github/workflows/campaign-report.yml`)
- النتيجة كتبان فـ Actions → آخر تشغيلة → Summary

هاد التقرير **مايبدل حتى حاجة** فالحساب — غير قراءة/تحليل. الهدف: تشوف الأداء ديال كل الحملات وتقرر واش خاصك تزيد حملة جديدة ولا لا.

## تدقيق شامل (Deep Audit) — جماهير، استهداف، كرياتيف، Funnel

سكريبت `meta_ads/campaign_audit.py` كيدير غوص عميق (قراءة فقط، مايبدل حتى حاجة) فـ:
- **الجماهير المخصصة (Custom Audiences)**: الأسماء، الحجم التقريبي، والمصدر (Website/Lookalike/Customer List...)
- **الاستهداف (Targeting)** لكل Ad Set فالحملات النشيطة + أحسن 5 حملات قديمة (حسب ROAS): العمر، الجنس، البلد، الاهتمامات، Custom Audiences المستعملة، Placements
- **الكرياتيف** لكل إعلان: النص، زر الـ CTA، الرابط
- **القمع الكامل (Funnel)**: View Content → Add to Cart → Initiate Checkout → Purchase، بالتكلفة فكل مرحلة

**كيفاش تشغلو:**
- Actions → **Meta Ads Deep Audit** → Run workflow
- النتيجة كتبان فـ Summary (تقرير طويل، خاصك تسكرولي)

هادشي كيعطينا الصورة الكاملة **علاش** حملة معينة خدمة مزيان (شنو الجمهور، شنو الاستهداف، شنو الكرياتيف)، ماشي غير قداش خدمة — باش نقدرو نكرروا النجاح فحملات جداد.

## تكرار حملة موجودة (Duplicate Campaign)

سكريبت `meta_ads/duplicate_campaign.py` كيدير نسخة كاملة (Campaign + Ad Sets + Ads، بنفس الجمهور والإعدادات) من حملة قديمة خدامة، باش ماتضطرش تبني كولشي من الصفر.

**مهم:** النسخة الجديدة كتتخلق **PAUSED** ديما — **مايبداش يصرف فلوس أوتوماتيك**. خاصك تدخل لـ Ads Manager، تراجع/تبدل الكرياتيف والمنتج، ومن بعد تفعلها يدويا ملي تكون راضي عليها.

**كيفاش تشغلو:**
- Actions → **Meta Ads Duplicate Campaign** → Run workflow
- عمر `source_campaign_name` باسم الحملة اللي بغيتي تكررها بالضبط (مثلا `Retargeting`)
- النتيجة (ID ديال الحملة الجديدة + رابط Ads Manager) كتبان فـ Summary

## 1) تحضير حساب Meta for Developers

1. سير لـ [developers.facebook.com](https://developers.facebook.com) ودخل بحساب الفيسبوك اللي عندو صلاحية على الـ Ad Account
2. **My Apps → Create App** → اختار نوع "Business"
3. من App Dashboard، زيد المنتج **Marketing API**
4. جيب:
   - **Ad Account ID**: من Ads Manager → Settings، شكلها `act_1234567890`
   - **Access Token طويل الأمد**: من [Graph API Explorer](https://developers.facebook.com/tools/explorer):
     - اختار الـ App ديالك
     - زيد الصلاحيات (Permissions): `ads_read`, `ads_management`
     - Generate Access Token
     - هاد التوكن قصير الأمد (ساعة)، خاصك تبدلو لطويل الأمد (60 يوم) عبر [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/) → "Extend Access Token"
5. للاستمرارية الكاملة (بلا ما يخصك تجدد التوكن كل 60 يوم)، الأحسن تصاوب **System User Token** من Business Settings → System Users (توكن دائم)

## 2) إعداد GitHub Secrets

فالريبو: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | القيمة |
|---|---|
| `META_ACCESS_TOKEN` | التوكن اللي جبتي |
| `META_AD_ACCOUNT_ID` | `act_XXXXXXXXXXXXX` |
| `TELEGRAM_BOT_TOKEN` | اختياري، للتنبيهات |
| `TELEGRAM_CHAT_ID` | اختياري، للتنبيهات |

## 3) تعديل القواعد

عدل `config.yaml` حسب الأهداف ديالك (target_cpa, increase_pct, min_daily_budget...). **خلي `dry_run: true`** فالبداية، وشغل الـ workflow يدويا (Actions → Meta Ads Daily Budget Optimizer → Run workflow) باش تشوف التقرير بلا ما يبدل شي حقيقي. ملي تتأكد اللي القرارات صافية، بدل `dry_run` لـ `false`.

## 4) الاختبار محليا (اختياري)

```bash
pip install -r requirements.txt
cp .env.example .env   # عمر القيم
export $(grep -v '^#' .env | xargs)
python -m meta_ads.main
```

## بنية المشروع

```
config.yaml                 # القواعد (بلا secrets)
meta_ads/
  config.py                 # قراءة config.yaml + secrets من env
  graph_api.py               # Meta Graph API client (insights, تبديل الميزانية، وقف)
  rules.py                   # منطق القرار (زيادة/نقصان/وقف)
  state.py                   # تتبع آخر تبديل لكل Ad Set (cooldown)
  alerts.py                  # تقرير GitHub Summary + Telegram
  main.py                    # التشغيل الرئيسي (تحسين الميزانية اليومي)
  report.py                  # منطق بناء تقرير الحملات
  campaign_report.py         # التشغيل الرئيسي (التقرير التحليلي الشامل)
  audit.py                   # منطق التدقيق الشامل (جماهير، استهداف، كرياتيف، funnel)
  campaign_audit.py          # التشغيل الرئيسي (التدقيق الشامل)
  duplicate_campaign.py      # تكرار حملة موجودة (PAUSED دايما)
.github/workflows/daily-budget-optimizer.yml   # الجدولة اليومية (تحسين الميزانية)
.github/workflows/campaign-report.yml          # التقرير التحليلي (يدوي + أسبوعي)
.github/workflows/campaign-audit.yml           # التدقيق الشامل (يدوي)
.github/workflows/duplicate-campaign.yml       # تكرار حملة (يدوي)
```

## ⚠️ ملاحظات أمان مهمة

- **ماتكتبش التوكن أبدا فالكود ولا فـ config.yaml** — غير عبر GitHub Secrets أو `.env` محلي (موجود فـ `.gitignore`)
- التوكنات ديال `ads_management` كيقدر يبدل فلوس حقيقية — خلي `dry_run: true` حتى تتأكد
- `max_daily_budget` و `min_daily_budget` فـ `config.yaml` هوما حد أمان باش السكريبت مايزيدش/ينقصش بزاف بلا حسيب
