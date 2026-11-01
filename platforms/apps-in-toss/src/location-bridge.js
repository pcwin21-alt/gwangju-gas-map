// The existing map requests location only after its explicit location action.
export function createLocationBridge(locationApi, accuracy) {
  let pending;
  async function locate() {
    const permission = await locationApi.getPermission();
    if (permission === 'notDetermined') {
      if (await locationApi.openPermissionDialog() !== 'allowed') throw new Error('위치 권한을 허용하지 않았어요. 지역·주소 검색을 이용해 주세요.');
    } else if (permission !== 'allowed') {
      throw new Error('위치 권한이 꺼져 있어요. 토스 설정에서 허용하거나 지역·주소 검색을 이용해 주세요.');
    }
    const result = await locationApi({accuracy});
    if (!Number.isFinite(result?.coords?.latitude) || !Number.isFinite(result?.coords?.longitude)) throw new Error('위치를 확인하지 못했어요. 잠시 후 다시 시도해 주세요.');
    return result;
  }
  return {
    getCurrentPosition(success, failure) {
      if (!pending) pending = locate().finally(() => { pending = null; });
      pending.then(success, failure);
    },
  };
}
