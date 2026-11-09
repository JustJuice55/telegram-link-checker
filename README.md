# Telegram Link Checker & Community Directory

Check what a public Telegram link actually opens. Browse a small, regularly checked directory of group chats.

[Community directory](#community-directory) · [Use the checker](#use-the-checker) · [GitHub Action](#check-a-list-in-github-actions) · [По-русски](README.ru.md)

Telegram can return **HTTP 200** for a generic contact page. A successful HTTP request alone does not show that a link still opens the group or channel described in your list.

This tool reads the public preview and reports what it finds. It needs Python 3.10+ and the standard library. No Telegram account, bot token or API key is required.

## Community directory

The first release covers jobs in Russia and Turkey, and education in Uzbekistan. Each entry has a direct Telegram link and a [TGDen](https://tgden.com/en/chats?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) catalog link with more details.

<!-- DIRECTORY:START -->

### Public community preview directory

Checked: **2026-11-09T13:54:00Z** (UTC). 34 listed communities from 36 distinct candidates.
Checks: community_preview=34, contact_only=2, bot_preview=0, inconclusive=0.

Only previews with member/subscriber evidence are listed. A fresh public preview is not an endorsement or verification of activity, safety, or geography.
Country and topic labels are TGDen's existing source filters. Counts below come from the observed Telegram preview.

#### Russia · Jobs (12)

| Community | Preview count | Public links |
| --- | ---: | --- |
| РАБОТА ВАХТА МОСКВА СПБ | 492,864 | [@vakansiit](https://t.me/vakansiit) · [TGDen card](https://tgden.com/en/chat/vakansiit?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| РАБОТА \| ВАКАНСИИ | 418,460 | [@moskva_vakhta_udalennaya_rf](https://t.me/moskva_vakhta_udalennaya_rf) · [TGDen card](https://tgden.com/en/chat/moskva_vakhta_udalennaya_rf?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Внимание Работа Москва | 277,128 | [@maskvadagi_tayanch](https://t.me/maskvadagi_tayanch) · [TGDen card](https://tgden.com/en/chat/maskvadagi_tayanch?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Мари про вакансии — инфобизнес | 190,483 | [@mari_vakansii](https://t.me/mari_vakansii) · [TGDen card](https://tgden.com/en/chat/mari_vakansii?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Работа Вакансии ВАХТОЙ | 147,520 | [@vakhta_rossia_rf](https://t.me/vakhta_rossia_rf) · [TGDen card](https://tgden.com/en/chat/vakhta_rossia_rf?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| ВНИМАНИЕ РАБОТА N1 | 92,617 | [@vnimanie_rabota_n1](https://t.me/vnimanie_rabota_n1) · [TGDen card](https://tgden.com/en/chat/vnimanie_rabota_n1?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| РАБОТА В ТАТАРСТАНЕ | 84,810 | [@kazanrabota_116](https://t.me/kazanrabota_116) · [TGDen card](https://tgden.com/en/chat/kazanrabota_116?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| MASKVA ISHLAR KVARTIRA | 63,258 | [@maskva_tanishuvf](https://t.me/maskva_tanishuvf) · [TGDen card](https://tgden.com/en/chat/maskva_tanishuvf?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| MOSKVA ISH GURUPPASI👷‍♂️ | 108,933 | [@maskva_ish_elonlar1](https://t.me/maskva_ish_elonlar1) · [TGDen card](https://tgden.com/en/chat/maskva_ish_elonlar1?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Чат⛑️\*SMSK\*🏗️Работа🌐Москва | 56,430 | [@smsk2020](https://t.me/smsk2020) · [TGDen card](https://tgden.com/en/chat/smsk2020?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| ФРИЛАНС ЧАТ \| ФРИЛАНС БИРЖА | 55,758 | [@frilancru](https://t.me/frilancru) · [TGDen card](https://tgden.com/en/chat/frilancru?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| ТОЛЬКО РОБОТА И ПОДРАБОТКА МОСКВА | 54,629 | [@moskva1717](https://t.me/moskva1717) · [TGDen card](https://tgden.com/en/chat/moskva1717?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |

#### Turkey · Jobs (12)

| Community | Preview count | Public links |
| --- | ---: | --- |
| Turkiyada ishlar 🇺🇿🇹🇷 | 57,715 | [@turkiyada_vakansiya](https://t.me/turkiyada_vakansiya) · [TGDen card](https://tgden.com/en/chat/turkiyada_vakansiya?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Turkiyada Ishlar \| O&\#x27;zbeklar uchun | 21,306 | [@turkiyau](https://t.me/turkiyau) · [TGDen card](https://tgden.com/en/chat/turkiyau?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| 🇹🇷TURKIYADAGI 🇺🇿ÖZBEKLARGA🇺🇿ISH🤝 | 9,246 | [@turkiyadaa_ishlar](https://t.me/turkiyadaa_ishlar) · [TGDen card](https://tgden.com/en/chat/turkiyadaa_ishlar?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| TURKIYA\_ISHONCHLI\_ISH Истанбул иш Вакансии в Турции | 2,816 | [@istanbul_ish_ishonchli](https://t.me/istanbul_ish_ishonchli) · [TGDen card](https://tgden.com/en/chat/istanbul_ish_ishonchli?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Работа в Турции | 1,205 | [@rabota_v_tursii](https://t.me/rabota_v_tursii) · [TGDen card](https://tgden.com/en/chat/rabota_v_tursii?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Анталья Все виды виз и внж Работа Переводы | 515 | [@turkiyejobs07100](https://t.me/turkiyejobs07100) · [TGDen card](https://tgden.com/en/chat/turkiyejobs07100?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| 🇹🇷🇺🇿Turkiya ish elonlari/ish bor🇰🇬🇹🇲 | 2,917 | [@ishborturkiya](https://t.me/ishborturkiya) · [TGDen card](https://tgden.com/en/chat/ishborturkiya?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| АНТАЛЬЯ ОБЪЯВЛЕНИЕ \(РАБОТА\) | 7,514 | [@antalyarabotatut](https://t.me/antalyarabotatut) · [TGDen card](https://tgden.com/en/chat/antalyarabotatut?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Стамбул работа | 6,933 | [@stambyl_rabota](https://t.me/stambyl_rabota) · [TGDen card](https://tgden.com/en/chat/stambyl_rabota?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Анталья \| Турция \- Работа Вакансии | 5,982 | [@antalia_work](https://t.me/antalia_work) · [TGDen card](https://tgden.com/en/chat/antalia_work?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Работа в Турции | 6,629 | [@rabota_inturkey](https://t.me/rabota_inturkey) · [TGDen card](https://tgden.com/en/chat/rabota_inturkey?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Работа в Турции | 5,064 | [@job_in_tr](https://t.me/job_in_tr) · [TGDen card](https://tgden.com/en/chat/job_in_tr?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |

#### Uzbekistan · Education (10)

| Community | Preview count | Public links |
| --- | ---: | --- |
| INGLIZ QUIZ | 19,069 | [@ingliz_testi](https://t.me/ingliz_testi) · [TGDen card](https://tgden.com/en/chat/ingliz_testi?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Ingliz quiz testlar🇺🇿 | 16,270 | [@ingliz_tili6](https://t.me/ingliz_tili6) · [TGDen card](https://tgden.com/en/chat/ingliz_tili6?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Ingiliz tilidan \| Quiz testlar📘 | 39,165 | [@ingliztestlarr](https://t.me/ingliztestlarr) · [TGDen card](https://tgden.com/en/chat/ingliztestlarr?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| INGLIZ TILIDAN QUIZ | 612 | [@ingliz_tilidan_quiz](https://t.me/ingliz_tilidan_quiz) · [TGDen card](https://tgden.com/en/chat/ingliz_tilidan_quiz?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| ЭЛИТНАЯ ШКОЛА\.РУССКИЙ ЯЗЫК \+ HD TV | 22,163 | [@e_maktab_rus_tili](https://t.me/e_maktab_rus_tili) · [TGDen card](https://tgden.com/en/chat/e_maktab_rus_tili?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| 🟡 Ассоциация Репетиторов\.uz | 12,955 | [@repetitori_uroki_studenti](https://t.me/repetitori_uroki_studenti) · [TGDen card](https://tgden.com/en/chat/repetitori_uroki_studenti?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| English zone quiz🎖 | 2,395 | [@english_zone_quiz](https://t.me/english_zone_quiz) · [TGDen card](https://tgden.com/en/chat/english_zone_quiz?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| QUIZ TESTLAR GURUHI | 1,139 | [@quiz_testlar_guruhi_n1](https://t.me/quiz_testlar_guruhi_n1) · [TGDen card](https://tgden.com/en/chat/quiz_testlar_guruhi_n1?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Русский язык\( ТРКИ\-C1,B2,B1\) | 759 | [@rustilic1_c2_b1_b2_test](https://t.me/rustilic1_c2_b1_b2_test) · [TGDen card](https://tgden.com/en/chat/rustilic1_c2_b1_b2_test?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |
| Ibratli Study \| Maths | 486 | [@ibratli_study_maths](https://t.me/ibratli_study_maths) · [TGDen card](https://tgden.com/en/chat/ibratli_study_maths?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map) |

Source: the [TGDen public API](https://tgden.com/api/v1/chats), three cohorts of at most 12 candidates; see [JSON data](data/communities.json) and [check audit](reports/directory-checks.json).

<!-- DIRECTORY:END -->

Download the [JSON snapshot](data/communities.json) or inspect the [preview check report](reports/directory-checks.json).

Country and topic come from TGDen catalog filters. They are useful starting points, not a manual verification of a group's location or subject. A public preview does not prove recent discussion, audience quality or safety.

## Use the checker

```bash
git clone https://github.com/JustJuice55/telegram-link-checker.git
cd telegram-link-checker

# Check public Telegram links in a local Markdown file.
python3 telegram_link_checker.py --file path/to/README.md \
  --json report.json --markdown report.md

# Check a public username directly.
python3 telegram_link_checker.py https://t.me/telegram
```

The checker deduplicates usernames and accepts public `t.me` / `telegram.me` links. It skips private invitation links. It checks at most 200 distinct links per run, with bounded requests and a signed User-Agent.

| Result | What it means |
| --- | --- |
| `community_preview` | The public preview shows a member or subscriber count. |
| `contact_only` | The page is a generic contact preview, without public community evidence. Review the link and its description. |
| `bot_preview` | The preview offers a Start Bot action. |
| `inconclusive` | A network error, challenge or unsupported page prevents a conclusion. |

`contact_only` does **not** mean deleted or banned. A username may have changed purpose. `inconclusive` does **not** mean unavailable. The checker reports evidence and never removes links from your files.

By default, a completed report does not fail your build over a contact-only result. Add `--fail-on-contact` when you want that result to require review in CI. Run `python3 telegram_link_checker.py --help` for options and exit behavior.

Exit codes: `0` completed checks, `1` contact-only review required by your policy, `2` input/report error, `3` inconclusive checks. Network uncertainty therefore remains visible to CI.

## Check a list in GitHub Actions

The reusable action writes a report to the run's step summary:

```yaml
name: Check Telegram links
on: [workflow_dispatch]
permissions:
  contents: read
jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 8
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: JustJuice55/telegram-link-checker@v1
        with:
          file: README.md
          fail-on-contact: 'false'
```

You choose when to run it and whether a contact-only result should fail the job. Review findings before changing a community list.

## Data and maintenance

The daily update workflow requests up to 12 candidates from each of three public TGDen API filters, then checks their public Telegram previews. Only candidates with community preview evidence enter the directory. The report records other observed results. If an API request or a preview check is inconclusive, the previous published snapshot is kept and the update run reports the failure.

The snapshot contains public usernames, titles, preview member/subscriber counts, country/topic filters, source links and check times. It contains no message text, personal profiles, private invitations or credentials. Displayed counts come from the Telegram preview at the time of the check.

Run the updater yourself:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/update_directory.py
```

Source: [TGDen public API](https://tgden.com/en/api-docs). TGDen is a catalog and search engine for public Telegram. [API and MCP examples](https://github.com/JustJuice55/tgden-api) are maintained separately.

## Contribute

Found a wrong topic, changed username or a preview the checker misreads? Open an issue with the public URL, the check time and the observed result. Do not include private invitation hashes, personal messages or credentials.

Useful contributions include better preview fixtures, language support and reproducible parser fixes. Community additions go through the source catalog and preview checks.

## License

Code: [MIT](LICENSE). Snapshot: [data terms](DATA-LICENSE.md). Names and trademarks belong to their respective owners. Listing a group does not imply endorsement.
