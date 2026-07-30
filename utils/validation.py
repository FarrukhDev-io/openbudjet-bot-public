def validate_luhn(card_number: str) -> bool:
    """Karta raqamini Luhn algoritmi bo'yicha tekshirish"""
    if not card_number.isdigit():
        return False
    r = [int(ch) for ch in card_number]
    return sum(r[-1::-2] + [sum(divmod(d * 2, 10)) for d in r[-2::-2]]) % 10 == 0


def validate_uz_card(card_number: str) -> bool:
    """Uzcard yoki Humo kartalarini prefiks va Luhn bo'yicha tekshirish"""
    if not card_number.isdigit() or len(card_number) != 16:
        return False
    if not (card_number.startswith("8600") or card_number.startswith("9860")):
        return False
    return validate_luhn(card_number)


def clean_phone_number(phone: str) -> str:
    """Telefon raqamini formatlash va 998 kodini qo'shish"""
    phone = phone.strip().replace("+", "").replace(" ", "").replace("-", "")
    if phone.startswith("7") and len(phone) == 11:
        phone = "998" + phone[2:]
    elif len(phone) == 9:
        phone = "998" + phone
    elif len(phone) == 10 and phone.startswith("0"):
        phone = "998" + phone[1:]
    elif not (len(phone) == 12 and phone.startswith("998")):
        if not phone.startswith("998"):
            phone = "998" + phone[-9:]
    return phone


def mask_card(card: str) -> str:
    """Karta raqamini qisman yashirish: 8600 **** **** 1234"""
    digits = card.replace(" ", "").replace("-", "")
    if len(digits) >= 8:
        return f"{digits[:4]} **** **** {digits[-4:]}"
    return card


def generate_p2p_links(card_number: str, amount: int) -> dict:
    """Uzbekistan to'lov tizimlari uchun oldindan to'ldirilgan P2P havolalarini yaratadi"""
    clean_card = card_number.replace(" ", "").replace("-", "")
    return {
        "click": f"https://my.click.uz/services/p2p?card_number={clean_card}&amount={amount}",
        "payme": f"https://checkout.paycom.uz/card-to-card?to={clean_card}&amount={amount * 100}",
        "uzum": f"https://uzumbank.uz/transfer?card={clean_card}&amount={amount}"
    }
