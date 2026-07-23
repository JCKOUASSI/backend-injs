export function mockSubmit(showToast, message) {
  return new Promise((resolve) => {
    setTimeout(() => {
      showToast(`${message} (enregistrement local — API serveur à connecter)`, 'success')
      resolve(true)
    }, 400)
  })
}
