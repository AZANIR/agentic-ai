#!/usr/bin/env bash
# Перевірка живого сервісу. ОДИН перелік проти будь-якої адреси.
#
#   ./deploy/smoke.sh https://localhost           локальна збірка
#   ./deploy/smoke.sh https://agentic.example     справжній домен
#
# Перелік не залежить від того, куди він дивиться, — і це головна властивість скрипта.
# Два різні переліки означали б, що локальний прогін доводить не те, що прогін на домені,
# і «здається, працює» повернулося б під іншою назвою.
#
# Локально сертифікат самопідписаний. Скрипт **не вимикає** перевірку мовчки: він каже
# вголос, що довіру до сертифіката не перевірено, і рахує це окремо від пройденого
# (spec AC-08). Мовчазний `--insecure` — це зелений колір за неперевірене.
#
# Вихід: 0, якщо всі перевірки пройшли; 1 — якщо хоч одна впала (AC-09, AC-09b).

set -uo pipefail

BASE="${1:-https://localhost}"
KEY="${API_KEY:-${SMOKE_API_KEY:-}}"
STARTED=$(date +%s)

PASSED=0
FAILED=0
UNVERIFIED=0

GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'; DIM=$'\033[2m'; OFF=$'\033[0m'

# Локальна адреса -> самопідписаний сертифікат. Прапорець ставиться усвідомлено й лише тут.
CURL=(curl --silent --show-error --max-time 10)
INSECURE=0
case "$BASE" in
	https://localhost*|https://127.0.0.1*)
		CURL+=(--insecure)
		INSECURE=1
		;;
esac

ok()   { PASSED=$((PASSED + 1)); printf '  %sok%s     %s\n' "$GREEN" "$OFF" "$1"; }
bad()  { FAILED=$((FAILED + 1)); printf '  %sЗБІЙ%s   %s %s(%s)%s\n' "$RED" "$OFF" "$1" "$DIM" "$2" "$OFF"; }
skip() { UNVERIFIED=$((UNVERIFIED + 1)); printf '  %s—%s      %s %s(%s)%s\n' "$YELLOW" "$OFF" "$1" "$DIM" "$2" "$OFF"; }

# Код відповіді на запит. Друкує рівно три цифри або 000, якщо зʼєднання не вдалося.
status_of() {
	local method="$1" path="$2"; shift 2
	"${CURL[@]}" --output /dev/null --write-out '%{http_code}' \
		--request "$method" "$@" "$BASE$path" 2>/dev/null || printf '000'
}

expect() {
	local name="$1" want="$2" got="$3"
	if [ "$got" = "$want" ]; then ok "$name"; else bad "$name" "очікували $want, отримали $got"; fi
}

printf '\nСмоук проти %s\n\n' "$BASE"

# --- 1. Сервіс живий, і стан не потребує ключа -------------------------------------------
HEALTH=$(status_of GET /healthz)
expect "стан відповідає без ключа" "200" "$HEALTH"

BODY=$("${CURL[@]}" "$BASE/healthz" 2>/dev/null || printf '')
# Порожнє тіло — збій, а не «нічого не розкрито». Без цього рядка перевірка нижче
# зеленіє на мертвому сервісі: у порожньому тілі справді немає рядка підключення.
if [ -z "$BODY" ]; then
	bad "стан повертає тіло" "порожня відповідь"
else
	ok "стан повертає тіло"
fi
# Верхній рівень, а не будь-де в тілі. Попередня редакція шукала «up» у всьому
# документі — і зеленіла на відповіді, де сервіс `down`, а одна із залежностей
# `up`. Перевірка знайшла потрібне слово не там, де стверджувала.
case "$BODY" in
	'{"status":"up"'*|'{ "status": "up"'*) ok "стан каже, що сервіс живий" ;;
	*) bad "стан каже, що сервіс живий" "тіло: ${BODY:0:140}" ;;
esac
case "$BODY" in
	*dependencies*) ok "стан називає залежності окремо" ;;
	*) bad "стан називає залежності окремо" "переліку немає" ;;
esac
# Дзеркальна половина: стан не має розкривати нічого, крім імен і станів.
case "$BODY" in
	*postgresql://*|*password*|*@*:*5432*) bad "стан не розкриває рядка підключення" "знайдено адресу" ;;
	*) ok "стан не розкриває рядка підключення" ;;
esac

# --- 2. Воротар пускає й не пускає --------------------------------------------------------
expect "запит без ключа відхилено" "401" \
	"$(status_of POST /ask --header 'content-type: application/json' --data '{"question":"привіт"}')"

expect "метрики без ключа відхилено" "401" "$(status_of GET /metrics)"

if [ -z "$KEY" ]; then
	skip "запит із ключем доходить" "ключа немає: постав API_KEY=..."
	skip "метрики з ключем віддаються" "ключа немає: постав API_KEY=..."
else
	expect "запит із ключем доходить" "200" \
		"$(status_of POST /ask --header 'content-type: application/json' \
			--header "x-api-key: $KEY" --data '{"question":"скільки днів на повернення"}')"
	expect "метрики з ключем віддаються" "200" \
		"$(status_of GET /metrics --header "x-api-key: $KEY")"
fi

# --- 3. Незашифроване зʼєднання перенаправляється ------------------------------------------
PLAIN="${BASE/https:/http:}"
REDIRECT=$("${CURL[@]}" --output /dev/null --write-out '%{http_code}' "$PLAIN/healthz" 2>/dev/null || printf '000')
case "$REDIRECT" in
	30[128]) ok "незашифроване зʼєднання перенаправляється" ;;
	*) bad "незашифроване зʼєднання перенаправляється" "код $REDIRECT" ;;
esac

# --- 4. Сертифікат ------------------------------------------------------------------------
if [ "$INSECURE" = "1" ]; then
	skip "сертифікат має довіру публічного центру" \
		"локальна адреса — сертифікат самопідписаний за побудовою"
else
	if curl --silent --show-error --max-time 10 --output /dev/null "$BASE/healthz" 2>/dev/null; then
		ok "сертифікат має довіру публічного центру"
	else
		bad "сертифікат має довіру публічного центру" "curl без --insecure не пройшов"
	fi
fi

TOOK=$(( $(date +%s) - STARTED ))
printf '\nпройдено %s, збоїв %s, не перевірено %s — за %s с\n' \
	"$PASSED" "$FAILED" "$UNVERIFIED" "$TOOK"

if [ "$UNVERIFIED" -gt 0 ]; then
	printf '%sНе перевірене — це не пройдене.%s Щоб закрити: реальний домен і API_KEY.\n' \
		"$YELLOW" "$OFF"
fi

[ "$FAILED" -eq 0 ] || exit 1
