# app/robokassa.py
import hashlib
import aiohttp
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class RobokassaService:
    BASE_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"
    CHECK_URL = "https://auth.robokassa.ru/Merchant/WebService/Service.asmx/OpStateExt"
    
    def generate_payment_link(
        self,
        amount: int,
        invoice_id: int,
        description: str,
    ) -> str:
        """Генерация ссылки на оплату"""
        signature_str = f"{settings.ROBOKASSA_LOGIN}:{amount}:{invoice_id}:{settings.ROBOKASSA_PASSWORD1}"
        signature = hashlib.md5(signature_str.encode()).hexdigest()
        
        params = {
            "MerchantLogin": settings.ROBOKASSA_LOGIN,
            "OutSum": amount,
            "InvId": invoice_id,
            "Description": description,
            "SignatureValue": signature,
        }
        
        if settings.ROBOKASSA_TEST_MODE:
            params["IsTest"] = 1
        
        return f"{self.BASE_URL}?{urlencode(params)}"
    
    async def check_payment_status(self, invoice_id: int) -> dict:
        """Проверка статуса платежа через XML API"""
        signature_str = f"{settings.ROBOKASSA_LOGIN}:{invoice_id}:{settings.ROBOKASSA_PASSWORD2}"
        signature = hashlib.md5(signature_str.encode()).hexdigest()
        
        params = {
            "MerchantLogin": settings.ROBOKASSA_LOGIN,
            "InvoiceID": invoice_id,
            "Signature": signature,
        }
        
        logger.info(f"Checking payment {invoice_id} with login={settings.ROBOKASSA_LOGIN}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.CHECK_URL, params=params) as response:
                    text = await response.text()
                    logger.info(f"Robokassa response for payment {invoice_id}: {text}")
                    return self._parse_response(text, invoice_id)
        except Exception as e:
            logger.error(f"Error checking payment {invoice_id}: {e}")
            return {'paid': False, 'reason': str(e)}
    
    def _parse_response(self, xml_text: str, invoice_id: int) -> dict:
        """Парсинг XML ответа от Robokassa"""
        try:
            xml_clean = xml_text.replace('xmlns="http://merchant.roboxchange.com/WebService/"', '')
            root = ET.fromstring(xml_clean)
            
            # Ищем State -> Code
            state = root.find('.//State')
            if state is not None:
                code = state.find('Code')
                if code is not None and code.text:
                    state_code = code.text
                    logger.info(f"Payment {invoice_id} StateCode: {state_code}")
                    
                    # 50, 80, 100 = оплачено
                    if state_code in ["50", "80", "100"]:
                        return {'paid': True}
                    else:
                        return {'paid': False, 'reason': f'StateCode: {state_code}'}
            
            # Ищем ошибку в Result
            result = root.find('.//Result')
            if result is not None:
                code = result.find('Code')
                desc = result.find('Description')
                code_text = code.text if code is not None else "?"
                desc_text = desc.text if desc is not None else "?"
                logger.warning(f"Payment {invoice_id} Result: {code_text} - {desc_text}")
                return {'paid': False, 'reason': f'{code_text}: {desc_text}'}
            
            logger.warning(f"Payment {invoice_id} unknown response format")
            return {'paid': False, 'reason': 'Unknown format'}
            
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}, content: {xml_text[:300]}")
            return {'paid': False, 'reason': f'Parse error: {e}'}


robokassa = RobokassaService()