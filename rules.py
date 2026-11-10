from .config import settings

def rules_text():
    return (
        f"**REGULAMENTO — FARM BOT**\\n"
        f"• Idade mínima padrão: **{settings.minimum_age} anos**.\\n"
        "• Proibidos cheats, scripts, exploits, macros não autorizadas e qualquer vantagem indevida.\\n"
        "• Proibidos falsificação de comprovante, compartilhamento de conta e fraude de inscrição.\\n"
        "• A inscrição só é confirmada após conferência bancária e aprovação manual.\\n"
        "• A organização pode solicitar evidências, analisar denúncias e aplicar sanções proporcionais."
    )
