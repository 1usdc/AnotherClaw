'\nTTS 路由：POST /api/tts 将文本转为语音，调用 utils.tts\n'
from fastapi import APIRouter,HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from utils import tts as tts_utils
router=APIRouter(tags=['tts'])
class TTSRequest(BaseModel):'TTS 请求体';text:str
@router.post('/api/tts')
async def post_tts(req:TTSRequest):
	'\n    将文本转为语音，返回 audio/mpeg。\n    使用 edge-tts（微软在线 TTS），免费无需 API Key。可选：OPENAGI_TTS_VOICE\n    ';B=(req.text or'').strip()
	if not B:raise HTTPException(status_code=400,detail='text 不能为空')
	try:C,D=await tts_utils.text_to_speech_async(B);return Response(content=C,media_type=D)
	except ValueError as A:raise HTTPException(status_code=400,detail=str(A))
	except ImportError:raise HTTPException(status_code=503,detail='edge-tts 包未安装，请执行: uv pip install edge-tts')
	except Exception as A:raise HTTPException(status_code=502,detail=f"TTS 调用失败: {A!s}")