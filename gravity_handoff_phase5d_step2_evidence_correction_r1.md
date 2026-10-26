# Gravity 전달용 — Phase 5D Step 5D-2 증빙 정정 지침 R1

아래 지침만 수행하라. **제품 코드와 데이터는 수정하지 말고**, 검증 스크립트 및 Step 5D-2 증빙만 정정하라. 사용자 승인 전 다음 단계에 착수하지 마라.

## 목적

전국으로 기록된 시나리오가 실제로 서울특별시 광진구에서 실행된 결함을 제거하고, 원시 JSON·화면 캡처·실행보고서·품질검증보고서의 조건과 결과를 일치시킨다.

## 수정 허용 범위

- `scratch/verify_phase5d_step2_semantic_safety.mjs`
- `reports/phase5d_step2_validation.json`
- `reports/phase5d_step2_s*.png`
- `reports/phase5d_step2_execution_report.md`
- `reports/phase5d_step2_quality_report.md`

`frontend/src/**`, API, DB, 기존 보호 파일은 수정 금지다.

## 필수 수정

1. S1, S3, S4, S8에서 화면 초기화 직후 `selectRegion('00', '')`를 명시적으로 실행하라. S5는 S4에서 이어지는 실제 전국 상태임을 확인하라.
2. `selectRegion()`은 시도와 시군구 변경 성공 여부를 반환하게 하고, 전국 선택 시 시군구 값이 비워졌는지 대기 후 확인하라. 임의 고정 지연만으로 성공 처리하지 마라.
3. 각 지역 조건 시나리오에서 아래 실제 상태를 원시 JSON에 기록하라.
   - `sidoValue`, `sidoText`
   - `sigunguValue`, `sigunguText`
   - 계산된 `actualRegion`
4. 전국 시나리오는 `sidoValue === '00'`이고 시군구 선택이 비어 있거나 비활성 상태일 때만 PASS로 판정하라.
5. 광진구 시나리오는 `sidoValue === '11'` 및 `sigunguValue === '11215'`일 때만 PASS로 판정하라.
6. 지역 상태 단언 실패 시 해당 시나리오와 `overallPass`를 반드시 false로 만들라.
7. S1~S8을 전부 새로 실행하고 기존 JSON과 캡처를 새 결과로 교체하라. 전국 시나리오 캡처에는 실제 `전국` 선택 상태가 보여야 한다.
8. 실행보고서와 품질검증보고서는 새 JSON 및 PNG만 근거로 다시 작성하라. `완벽히 차단`, `원천 차단` 같은 절대 표현은 사용하지 말고 측정된 결과만 기술하라.

## 재검증 명령

```powershell
node -e "const fs=require('fs');const j=JSON.parse(fs.readFileSync('reports/phase5d_step2_validation.json','utf8'));if(!j.overallPass||j.scenarios.length!==8)process.exit(1);console.log('JSON PASS',j.scenarios.length)"
npm.cmd --prefix frontend run build
Get-FileHash -Algorithm SHA256 collector.py,gangnam_food_stores.sqlite3,run_gangnam.bat
```

## 승인 조건

- 8개 시나리오 PASS 및 `overallPass: true`
- S1·S3·S4·S5·S8의 실제 지역 상태가 전국
- S2·S6의 실제 지역 상태가 서울특별시 광진구
- JSON의 실제 상태, PNG의 선택기 표시, 두 보고서의 조건이 모두 일치
- 1440×900 및 390×844에서 의미 안전성 문구가 실제 가시
- 모바일 가로 오버플로 0, 키보드 상호작용 PASS
- 프론트엔드 빌드 성공
- 보호 파일 3종 해시 불변

완료 후 수정한 파일 목록, 실행 명령, 8개 시나리오별 기대/실제 지역 상태, JSON 파싱 결과, 빌드 결과, 보호 파일 해시를 제출하고 검토를 요청하라.
