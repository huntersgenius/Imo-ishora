# IMO-ISHORA Source Reference

This file stores reference information, decisions, and source vocabulary for the IMO-ISHORA prompt set.

## Date Baseline

Reference date: 2026-06-05

## Final Technology Decisions

| Layer | Final decision | Alternatives considered | Decision basis |
|---|---|---|---|
| Backend API | FastAPI with Pydantic v2 direction | Litestar, Starlette, Django Ninja | Best fit for a small typed async API with OpenAPI docs and broad ecosystem support |
| Video processing | FFmpeg-first processing from Python orchestration | MoviePy, PyAV, vidgear | Better memory profile, native concat and normalization, mature browser-compatible encoding |
| R2 integration | boto3 using Cloudflare R2 S3-compatible API | Cloudflare SDK, direct HTTP | Mature object operations, metadata checks, uploads, and signed URL support |
| Processing concurrency | Async subprocess orchestration with bounded job concurrency | Process pools, thread pools, Celery | FFmpeg runs outside Python; a broker is unnecessary for MVP |
| Frontend framework | Vite 8 with React 19.2 and TypeScript | Next.js, Astro, SvelteKit | Single-page app with separate backend does not need SSR or framework server features |
| Animation | Motion for React | GSAP, React Spring, Motion One, AutoAnimate | Best React fit for phase transitions, layout animation, and word-chip stagger |
| State | Zustand v5 | React state, Jotai, Nanostores, Valtio | One compact workflow store with minimal ceremony |
| Styling | Vanilla CSS with CSS custom properties | Tailwind CSS, CSS Modules, UnoCSS | Bespoke design with direct control over tokens, motion, and responsive polish |
| Video player | Custom HTML5 video player | react-player, Vidstack, Plyr | Small MP4 playback with full product-specific UI control |
| Persistent media storage | Cloudflare R2 | Filesystem media library, object stores from other vendors | R2 is the selected source of truth for source clips and generated outputs |

## Current Documentation Facts

| Topic | Fact |
|---|---|
| Cloudflare R2 boto3 | R2 supports S3-compatible access through boto3 when configured with the account-specific endpoint URL and region value `auto`. |
| Cloudflare R2 signed URLs | Signed URLs are generated for specific S3 operations and are useful for temporary access. They use the R2 S3 API domain, not a custom-domain URL. |
| Cloudflare R2 public access | Public access can use a Cloudflare-managed development URL or a custom domain; custom domains enable Cloudflare cache and security features. |
| Cloudflare R2 CORS | Browser access to public objects or signed URLs needs an R2 CORS policy matching the frontend origin and methods. |
| FastAPI | Recent FastAPI releases are aligned with Pydantic v2, and old Pydantic v1 paths are deprecated or removed in newer releases. |
| Vite | Vite 8 is the current major line and uses a modern supported browser baseline; supported patch lines include Vite 8 and backports for recent older majors. |
| React | React documentation identifies React 19.2 as the latest major-version documentation target. |
| Motion | Current Motion for React docs use the `motion` package naming and Motion React API for features such as AnimatePresence. |
| FFmpeg concat | FFmpeg documents multiple concat strategies; concat filter is appropriate when normalization and re-encoding are needed. |

## Slovo Dataset Facts

| Fact | Value |
|---|---|
| Dataset | Slovo Russian Sign Language Dataset |
| Public reference | hukenovs/slovo GitHub repository and associated paper |
| Approximate size | About 16 GB for the trimmed main dataset |
| Video count | About 20,400 RGB videos in the repository description |
| Class count | 1,000 sign language gestures |
| Signers | 194 signers |
| Samples per class | 20 samples per class in the repository description |
| Splits | Training and test sets split by subject identifier |
| Typical content | Isolated Russian Sign Language gestures and short glosses |
| Important caveat | Dataset classes use Russian labels or class identifiers, not guaranteed transliterated filenames |
| Product implication | Admin preparation later consists of clean sample selection, normalization or approval, R2 upload, and object metadata entry in `r2_video_inventory.csv` |

## R2 Metadata Fields

| Field | Meaning |
|---|---|
| uzbek_word | Canonical Uzbek dictionary key or phrase |
| russian_gloss | Russian sign gloss expected to map to a Slovo or curated RSL clip |
| category | Product category used for filtering, stats, and QA |
| r2_key | Cloudflare R2 object key for the curated source clip |
| public_url | Public custom-domain URL when the object is intended for public playback or inspection |
| content_type | Media content type, normally video/mp4 |
| duration_seconds | Clip duration after admin inspection |
| width | Source video width |
| height | Source video height |
| fps | Source video frame rate |
| codec | Source video codec |
| orientation | portrait, landscape, or square |
| quality_status | missing, needs_review, demo_ready, rejected |
| signer_sample_note | Human note identifying selected signer or sample quality |
| admin_note | Freeform owner note |

## Canonical Vocabulary Seed

This seed reflects a cleaned initial selection derived from the research material. Conflicts are resolved for MVP usefulness.

| Uzbek | Russian | Category |
|---|---|---|
| salom | привет | greeting |
| assalomu alaykum | здравствуйте | greeting |
| xayr | пока | greeting |
| hayr | пока | greeting |
| ko'rishguncha | до свидания | greeting |
| xush kelibsiz | добро пожаловать | greeting |
| yaxshi kun | добрый день | greeting |
| xayrli kech | добрый вечер | greeting |
| xayrli tun | спокойной ночи | greeting |
| salomlashish | приветствие | greeting |
| rahmat | спасибо | polite |
| katta rahmat | большое спасибо | polite |
| iltimos | пожалуйста | polite |
| kechirasiz | извините | polite |
| uzr | прости | polite |
| marhamat | пожалуйста | polite |
| albatta | конечно | polite |
| men | я | pronoun |
| sen | ты | pronoun |
| u | он | pronoun |
| biz | мы | pronoun |
| siz | вы | pronoun |
| ular | они | pronoun |
| bu | это | pronoun |
| o'sha | тот | pronoun |
| hamma | все | pronoun |
| o'zi | сам | pronoun |
| nima | что | question |
| kim | кто | question |
| qayerda | где | question |
| qachon | когда | question |
| qanday | как | question |
| necha | сколько | question |
| nega | почему | question |
| qaysi | какой | question |
| qayer | куда | question |
| qancha | сколько | question |
| ona | мама | family |
| ota | папа | family |
| aka | брат | family |
| opa | сестра | family |
| bola | ребёнок | family |
| oila | семья | family |
| buva | дедушка | family |
| buvi | бабушка | family |
| er | муж | family |
| xotin | жена | family |
| o'g'il | сын | family |
| qiz | дочь | family |
| amaki | дядя | family |
| xola | тётя | family |
| jiyan | племянник | family |
| bir | один | number |
| ikki | два | number |
| uch | три | number |
| to'rt | четыре | number |
| besh | пять | number |
| olti | шесть | number |
| yetti | семь | number |
| sakkiz | восемь | number |
| to'qqiz | девять | number |
| o'n | десять | number |
| o'n bir | одиннадцать | number |
| o'n ikki | двенадцать | number |
| o'n uch | тринадцать | number |
| o'n to'rt | четырнадцать | number |
| o'n besh | пятнадцать | number |
| o'n olti | шестнадцать | number |
| o'n yetti | семнадцать | number |
| o'n sakkiz | восемнадцать | number |
| o'n to'qqiz | девятнадцать | number |
| yigirma | двадцать | number |
| qizil | красный | color |
| ko'k | синий | color |
| yashil | зелёный | color |
| sariq | жёлтый | color |
| oq | белый | color |
| qora | чёрный | color |
| pushti | розовый | color |
| jigarrang | коричневый | color |
| to'q sariq | оранжевый | color |
| kulrang | серый | color |
| bormoq | идти | action |
| kelmoq | приходить | action |
| yemoq | есть | action |
| ichmoq | пить | action |
| o'qimoq | читать | action |
| o'rganmoq | учиться | action |
| yozmoq | писать | action |
| gapirmoq | говорить | action |
| tinglamoq | слушать | action |
| ko'rmoq | смотреть | action |
| bilmoq | знать | action |
| xohlamoq | хотеть | action |
| qilmoq | делать | action |
| ishlamoq | работать | action |
| o'ynamoq | играть | action |
| sevmoq | любить | action |
| yordam bermoq | помогать | action |
| bermoq | давать | action |
| olmoq | брать | action |
| yashamoq | жить | action |
| uxlamoq | спать | action |
| turmoq | стоять | action |
| o'tirmoq | сидеть | action |
| yugurmoq | бежать | action |
| kutmoq | ждать | action |
| sotib olmoq | купить | action |
| tushunmoq | понимать | action |
| o'ylamoq | думать | action |
| eslamoq | помнить | action |
| unutmoq | забыть | action |
| ochmoq | открыть | action |
| yopmoq | закрыть | action |
| boshlamoq | начать | action |
| tugatmoq | закончить | action |
| ko'chmoq | переехать | action |
| baxtli | счастливый | emotion |
| xursand | радостный | emotion |
| qayg'uli | грустный | emotion |
| g'azablangan | злой | emotion |
| xavotirli | тревожный | emotion |
| yaxshi | хорошо | emotion |
| yomon | плохо | emotion |
| tinch | спокойный | emotion |
| charchagan | уставший | emotion |
| kasal | больной | emotion |
| sog'lom | здоровый | emotion |
| hayron | удивлённый | emotion |
| qo'rqinchli | страшный | emotion |
| xafa | обиженный | emotion |
| bugun | сегодня | time |
| ertaga | завтра | time |
| kecha | вчера | time |
| hozir | сейчас | time |
| ertalab | утром | time |
| tushlik | обед | time |
| kechqurun | вечером | time |
| tun | ночь | time |
| hafta | неделя | time |
| oy | месяц | time |
| yil | год | time |
| soat | час | time |
| daqiqa | минута | time |
| doim | всегда | time |
| hech qachon | никогда | time |
| uy | дом | object |
| maktab | школа | object |
| suv | вода | object |
| ovqat | еда | object |
| kitob | книга | object |
| shahar | город | object |
| mamlakat | страна | object |
| do'st | друг | object |
| shifokor | врач | object |
| o'qituvchi | учитель | object |
| ish | работа | object |
| mashina | машина | object |
| telefon | телефон | object |
| pul | деньги | object |
| do'kon | магазин | object |
| kasalxona | больница | object |
| ko'cha | улица | object |
| park | парк | object |
| odam | человек | object |
| erkak | мужчина | object |
| ayol | женщина | object |
| non | хлеб | object |
| sut | молоко | object |
| meva | фрукт | object |
| sabzavot | овощ | object |
| kiyim | одежда | object |
| poyabzal | обувь | object |
| stol | стол | object |
| stul | стул | object |
| deraza | окно | object |
| katta | большой | adjective |
| kichik | маленький | adjective |
| yangi | новый | adjective |
| eski | старый | adjective |
| chiroyli | красивый | adjective |
| issiq | горячий | adjective |
| sovuq | холодный | adjective |
| tez | быстрый | adjective |
| sekin | медленный | adjective |
| kuchli | сильный | adjective |
| uzun | длинный | adjective |
| kalta | короткий | adjective |
| og'ir | тяжёлый | adjective |
| yengil | лёгкий | adjective |
| to'g'ri | правильный | adjective |
| noto'g'ri | неправильный | adjective |
| muhim | важный | adjective |
| oson | лёгкий | adjective |
| ha | да | basic |
| yo'q | нет | basic |
| bor | есть | basic |
| kerak | нужно | basic |
| mumkin | можно | basic |
| shart | обязательно | basic |
| balki | может быть | basic |
| faqat | только | basic |

## Ambiguity Decisions

| Uzbek | Chosen gloss | Deferred gloss | Reason |
|---|---|---|---|
| yaxshi | хорошо | хороший | Demo phrases often use it as a state or answer |
| yomon | плохо | плохой | State meaning is more useful for early demo feedback |
| tez | быстрый | скоро | Adjective meaning avoids conflict with time phrase usage |
| er | муж | мужчина | Family meaning is common; `erkak` covers man |
| o'qimoq | читать | учиться | Read and study are separated through `o'rganmoq` |
| bola | ребёнок | duplicate entry | Exact duplicate removed |

## Uzbek Suffix Reference

| Group | Suffixes |
|---|---|
| Longest-first stripping list | moqda, yotir, yotgan, moqchi, aylik, ingiz, imiz, lari, miz, lar, ning, gan, dan, adi, ydi, lik, siz, roq, man, san, sin, ish, chi, da, ga, ni, li, di, ar, im, ng, in, si, i |
| Case suffixes | ning, ni, ga, da, dan |
| Possessive suffixes | im, ing, i, si, imiz, ingiz, lari |
| Verb tense suffixes | moqda, yotir, yotgan, adi, ydi, di, gan, ar, moqchi |
| Verb person suffixes | man, san, miz, siz, lar |
| Mood and aspect suffixes | ish, ma, mas, sin, ing, aylik |
| Adjective suffixes | li, siz, lik, roq, gina |

## Reference Links

| Topic | URL |
|---|---|
| Cloudflare R2 boto3 | https://developers.cloudflare.com/r2/examples/aws/boto3/ |
| Cloudflare R2 CORS | https://developers.cloudflare.com/r2/buckets/cors/ |
| Cloudflare R2 public buckets | https://developers.cloudflare.com/r2/buckets/public-buckets/ |
| FastAPI release notes | https://fastapi.tiangolo.com/release-notes/ |
| Vite releases | https://vite.dev/releases |
| React versions | https://react.dev/versions |
| Motion AnimatePresence | https://motion.dev/docs/react-animate-presence |
| FFmpeg concat FAQ | https://ffmpeg.org/faq.html |
| Slovo dataset | https://github.com/hukenovs/slovo |
