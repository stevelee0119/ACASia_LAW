# 중간 배포 식별과 실행 환경

- 점검 시작: 2026-11-19 05:51 KST (2026-11-18 20:51 UTC)
- 서비스: `https://verify-acas-law.onrender.com`
- `GET /api/health`: HTTP 200. 배포 SHA와 DB가 처음 조회에서 일치하여 재시도하지 않았다.
- 이 배포는 버전 문자열이 `0.22.0`인 0.23.0 중간 배포다. 빌드 식별자는 아래 전체 commit이다.

```json
{
  "status": "ok",
  "app": "ACASia_LAW",
  "version": "0.22.0",
  "commit": "32d9c485bc04ef0487fc4c6a32a91c9d39d29948",
  "principles": ["Source First", "Evidence First", "Human Final Decision"],
  "database": {"status": "ok"}
}
```

모든 아래 보고서의 `run_manifest.implementation.git_commit`도 위 SHA와 대조했다. 원본 응답과 보고서는 저장소 외부의 접근 제한 보관소에 해시와 함께 보존한다.

브라우저 자동화는 Chromium의 `ignoreHTTPSErrors`를 켜서 실행했다. 이 환경의 Chromium 기본 인증서 검증은 실패했으므로 브라우저의 TLS 설정 자체를 운영 성공으로 판정하지 않는다. 별도 Python API 클라이언트는 기본 인증서 검증으로 HTTPS 호출에 성공했다.
