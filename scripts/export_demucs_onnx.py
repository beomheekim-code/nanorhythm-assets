# -*- coding: utf-8 -*-
"""Demucs htdemucs_6s PyTorch 모델 → ONNX export.
   UGC 클라이언트 측 stem 분리 (WASM Demucs) 용.

사용법:
  pip install torch onnx demucs
  python scripts/export_demucs_onnx.py
  → output: htdemucs_6s.onnx (250 MB) + htdemucs_6s_fp16.onnx (양자화, 120 MB)

업로드:
  1. HuggingFace 계정 생성 (https://huggingface.co/join)
  2. 새 model repo 만들기 (https://huggingface.co/new) — public, repo 이름 'nanorhythm-demucs'
  3. 파일 업로드 (브라우저 drag&drop):
     - htdemucs_6s_fp16.onnx
     - README.md (모델 출처 + 라이선스)
  4. URL 확보:
     https://huggingface.co/<USER>/nanorhythm-demucs/resolve/main/htdemucs_6s_fp16.onnx

알고리즘:
  - htdemucs_6s = HTDemucs 6 stem (drums/bass/vocals/other/piano/guitar)
  - 입력: stereo 44100Hz audio (segment 단위, 7.8초 = 343750 samples)
  - 출력: 6 channel × stereo (각 stem 별 stereo audio)
  - WASM 추론: ONNX Runtime Web (WebAssembly backend)
"""
import os
import sys
import torch
import torch.onnx
from demucs.pretrained import get_model
from demucs.apply import apply_model

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OUT_DIR = os.path.abspath(os.path.dirname(__file__) + '/../onnx_models')
os.makedirs(OUT_DIR, exist_ok=True)


def export_htdemucs():
    print('[1/3] htdemucs_6s 모델 다운로드 (250 MB)...')
    model = get_model('htdemucs_6s')
    model.eval()

    # Demucs 는 (batch, channels=2, samples) 입력
    # segment 길이: htdemucs default = 7.8s = 343750 samples @ 44100Hz
    segment_samples = 343750
    sr = 44100

    print(f'[2/3] ONNX export (input shape: 1×2×{segment_samples})...')
    dummy = torch.randn(1, 2, segment_samples)

    out_path = os.path.join(OUT_DIR, 'htdemucs_6s.onnx')
    torch.onnx.export(
        model,
        dummy,
        out_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['audio'],
        output_names=['stems'],  # shape: (1, 6, 2, segment_samples)
        dynamic_axes={
            'audio': {2: 'samples'},     # 가변 길이
            'stems': {3: 'samples'},
        },
    )
    print(f'    → {out_path}')

    # 양자화 (FP32 → FP16): size 250MB → 125MB
    print('[3/3] FP16 양자화...')
    import onnx
    from onnxconverter_common import float16
    m_fp32 = onnx.load(out_path)
    m_fp16 = float16.convert_float_to_float16(m_fp32, keep_io_types=True)
    fp16_path = os.path.join(OUT_DIR, 'htdemucs_6s_fp16.onnx')
    onnx.save(m_fp16, fp16_path)
    size_mb = os.path.getsize(fp16_path) / (1024 * 1024)
    print(f'    → {fp16_path} ({size_mb:.1f} MB)')

    return fp16_path


if __name__ == '__main__':
    try:
        path = export_htdemucs()
        print(f'\n[완료] {path}')
        print('\n다음 단계:')
        print('  1. HuggingFace 계정 가입 (https://huggingface.co/join)')
        print('  2. 새 model repo 만들기: nanorhythm-demucs (public)')
        print('  3. 위 파일 업로드 (drag&drop)')
        print('  4. URL 확보 후 Claude 에게 알려주기')
    except Exception as e:
        print(f'\n[실패] {e}')
        import traceback
        traceback.print_exc()
