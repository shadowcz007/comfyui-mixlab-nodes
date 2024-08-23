export const base64Df =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAAAXNSR0IArs4c6QAAALZJREFUKFOFkLERwjAQBPdbgBkInECGaMLUQDsE0AkRVRAYWqAByxldPPOWHwnw4OBGye1p50UDSoA+W2ABLPN7i+C5dyC6R/uiAUXRQCs0bXoNIu4QPQzAxDKxHoALOrZcqtiyR/T6CXw7+3IGHhkYcy6BOR2izwT8LptG8rbMiCRAUb+CQ6WzQVb0SNOi5Z2/nX35DRyb/ENazhpWKoGwrpD6nICp5c2qogc4of+c7QcrhgF4Aa/aoAFHiL+RAAAAAElFTkSuQmCC'

export function getUrl () {
  let api_host = `${window.location.hostname}:${window.location.port}`
  let api_base = ''
  let url = `${window.location.protocol}//${api_host}${api_base}`
  return url
}

// 获得插件/节点的索引数据
export async function get_nodes_map () {
  let url = getUrl()

  const res = await fetch(`${url}/mixlab/nodes_map`, {
    method: 'POST',
    body: JSON.stringify({
      data: 'json'
    })
  })
  return await res.json()
}

// 更新或者获取key
export const updateLLMAPIKey = async key => {
  try {
    const res = await fetch(`${getUrl()}/mixlab/llm_api_key`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        key: key || null
      })
    })

    const data = await res.json()

    if (!res.ok) {
      console.error('Error:', data.error)
      return
    }

    if (key) {
      console.log('API key saved successfully:', data.message)
      return key
    } else {
      console.log('Retrieved API key:', data.key)
      return data.key
    }
  } catch (error) {
    console.error('Request failed:', error)
  }
}

//获取当前系统的插件，节点清单
export function getObjectInfo () {
  return new Promise(async (resolve, reject) => {
    let url = getUrl()

    try {
      const response = await fetch(`${url}/object_info`)
      const data = await response.json()
      resolve(data)
    } catch (error) {
      reject(error)
    }
  })
}

export function get_position_style (
  ctx,
  widget_width,
  y,
  node_height,
  left = 44
) {
  const MARGIN = 0 // the margin around the html element

  /* Create a transform that deals with all the scrolling and zooming */
  const elRect = ctx.canvas.getBoundingClientRect()

  const scaleX = elRect.width / ctx.canvas.width
  const scaleY = elRect.height / ctx.canvas.height

  const transform = new DOMMatrix()
    .scaleSelf(scaleX, scaleY)
    .multiplySelf(ctx.getTransform())
    .translateSelf(MARGIN, MARGIN + y)

  return {
    transformOrigin: '0 0',
    transform: transform,
    left:
      document.querySelector('.comfy-menu').style.display === 'none'
        ? `${left}px`
        : `0`,
    top: `0`,
    cursor: 'pointer',
    position: 'absolute',
    maxWidth: `${widget_width - MARGIN * 2}px`,
    // maxHeight: `${node_height - MARGIN * 2}px`, // we're assuming we have the whole height of the node
    width: `${widget_width - MARGIN * 2}px`,
    height: `${node_height * 0.3 - MARGIN * 2}px`,
    // background: '#EEEEEE',
    display: 'flex',
    flexDirection: 'column',
    // alignItems: 'center',
    justifyContent: 'flex-start',
    zIndex: 99
  }
}

export function loadCSS (url) {
  var link = document.createElement('link')
  link.rel = 'stylesheet'
  link.type = 'text/css'
  link.href = url
  document.getElementsByTagName('head')[0].appendChild(link)
}


export function injectCSS (css) {
  // 检查页面中是否已经存在具有相同内容的style标签
  const existingStyle = document.querySelector('style')
  if (existingStyle && existingStyle.textContent === css) {
    return // 如果已经存在相同的样式，则不进行注入
  }

  // 创建一个新的style标签，并将CSS内容注入其中
  const style = document.createElement('style')
  style.textContent = css

  // 将style标签插入到页面的head元素中
  const head = document.querySelector('head')
  head.appendChild(style)
}


export function loadExternalScript (url, type) {
  return new Promise((resolve, reject) => {
    const existingScript = document.querySelector(`script[src="${url}"]`)
    if (existingScript) {
      existingScript.onload = () => {
        resolve()
      }
      existingScript.onerror = reject
      return
    }

    const script = document.createElement('script')
    script.src = url
    if (type) script.type = type // Add this line to load the script as an ES module
    script.onload = () => {
      resolve()
    }
    script.onerror = reject
    document.head.appendChild(script)
  })
}

export async function getQueue () {
  try {
    const res = await fetch(`${getUrl()}/queue`)
    const data = await res.json()
    // console.log(data.queue_running,data.queue_pending)
    return {
      // Running action uses a different endpoint for cancelling
      Running: data.queue_running.length,
      Pending: data.queue_pending.length
    }
  } catch (error) {
    console.error(error)
    return { Running: 0, Pending: 0 }
  }
}

export async function interrupt () {
  const resp = await fetch(`${getUrl()}/interrupt`, {
    method: 'POST'
  })
}

export async function sleep (t = 200) {
  return new Promise((res, rej) => {
    setTimeout(() => {
      res(true)
    }, t)
  })
}

export function createImage (url) {
  let im = new Image()
  return new Promise((res, rej) => {
    im.onload = () => res(im)
    im.src = url
  })
}

export function convertImageUrlToBase64 (imageUrl) {
  return fetch(imageUrl)
    .then(response => response.blob())
    .then(blob => {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onloadend = () => resolve(reader.result)
        reader.onerror = reject
        reader.readAsDataURL(blob)
      })
    })
}

export const getLocalData = key => {
  let data = {}
  try {
    data = JSON.parse(localStorage.getItem(key)) || {}
  } catch (error) {
    return {}
  }
  return data
}

export const saveLocalData = (key, id, val) => {
  let data = getLocalData(key)
  data[id] = val
  localStorage.setItem(key, JSON.stringify(data))
}
