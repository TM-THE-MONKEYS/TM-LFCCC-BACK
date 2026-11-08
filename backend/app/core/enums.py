from enum import StrEnum


class UserRole(StrEnum):
    admin = "admin"
    operator = "operator"


class ProductCategory(StrEnum):
    camiseta = "camiseta"
    calca = "calca"
    vestido = "vestido"
    saia = "saia"
    jaqueta = "jaqueta"
    calcado = "calcado"
    acessorio = "acessorio"
    outro = "outro"


class ClothingSize(StrEnum):
    PP = "PP"
    P = "P"
    M = "M"
    G = "G"
    GG = "GG"
    XGG = "XGG"
    size_36 = "36"
    size_38 = "38"
    size_40 = "40"
    size_42 = "42"
    size_44 = "44"
    size_46 = "46"
    size_48 = "48"


class PaymentMethod(StrEnum):
    dinheiro = "dinheiro"
    cartao_credito = "cartao_credito"
    cartao_debito = "cartao_debito"
    pix = "pix"
    boleto = "boleto"


class DonationDirection(StrEnum):
    recebida = "recebida"
    doada = "doada"


class DonationCategory(StrEnum):
    dinheiro = "dinheiro"
    roupas = "roupas"
    calcados = "calcados"
    acessorios = "acessorios"
    alimentos = "alimentos"
    outros = "outros"
