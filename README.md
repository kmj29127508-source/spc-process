# 📊 반도체 박막증착 공정 SPC & 공정능력분석 대시보드

스마트제조 기말 프로젝트 — 강의록 08(공정능력분석), 09(통계적공정관리) 내용을 기반으로 구현한
Streamlit 웹앱입니다.

## 주요 기능

- **데이터 업로드**: 계량형(부분군별 측정값) / 계수형(로트별 불량수) CSV 파일을 업로드하면
  새로운 공정능력분석 + SPC 분석이 즉시 재계산됩니다. (업로드하지 않으면 샘플 데이터로 동작)
- **공정능력분석**: 정규성 검정(Shapiro-Wilk), Q-Q Plot, Cp/Cpk(군내변동), Pp/Ppk(전체변동)
  자동 계산 및 등급 판정
- **계량형 관리도**: Xbar-R, Xbar-S, I-MR (윈도우 크기 조절 가능)
- **계수형 관리도**: P, NP (표본크기 동일여부 자동 체크)
- **이상 판정**: Nelson's Rule 1/2/3/5/6 자동 판정 및 시각화
- **Phase I 개선**: Rule1(관리한계 이탈) 부분군 반복 제거 및 관리한계 재계산
- **종합 대시보드**: 한눈에 보는 Cpk/Ppk, 이상점 현황, 정규성, 불량률 추이

## 로컬 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

## 데이터 파일 형식

### 계량형 (measurements.csv)
```
x1,x2,x3,x4,x5
106,94,103,97,100
98,100,96,103,93
...
```
(1행 = 1개 부분군, 열은 측정 지점 수만큼 자유롭게 변경 가능)

### 계수형 (defects.csv)
```
로트,검사수,불량수
1,200,5
2,200,7
...
```

## 배포 (Streamlit Community Cloud)

1. GitHub에 본 폴더(app.py, spc_lib.py, requirements.txt, measurements.csv, defects.csv)를 push
2. https://share.streamlit.io 접속 → New app
3. 본인 GitHub 저장소 선택, Main file path를 `app.py`로 지정
4. Deploy 클릭

## 기술 스택

- Streamlit (웹앱 프레임워크)
- Pandas / NumPy (데이터 처리)
- Plotly (인터랙티브 시각화)
- SciPy (정규성 검정, Box-Cox)

## 작성자

스마트제조 기말 프로젝트
