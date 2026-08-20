const DEVICE_KEY = 'injs_badge_device_id'

export function getBadgeDeviceId() {
  let id = localStorage.getItem(DEVICE_KEY)
  if (!id) {
    id = (crypto.randomUUID && crypto.randomUUID()) || `web-${Date.now()}-${Math.random().toString(16).slice(2)}`
    localStorage.setItem(DEVICE_KEY, id)
  }
  return id
}

export async function captureBadgeContext() {
  const device_id = getBadgeDeviceId()
  const device_label = (navigator.userAgent || 'web').slice(0, 120)
  const context = { device_id, device_label }

  if (!navigator.geolocation) {
    return context
  }

  try {
    const position = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 20000,
      })
    })
    context.latitude = position.coords.latitude
    context.longitude = position.coords.longitude
    context.accuracy_m = position.coords.accuracy
  } catch {
    // Le backend décide si le GPS est obligatoire pour la salle.
  }

  return context
}
