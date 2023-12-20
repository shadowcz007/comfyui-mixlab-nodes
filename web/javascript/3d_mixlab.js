import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { $el } from '../../../scripts/ui.js'

const getLocalData = key => {
  let data = {}
  try {
    data = JSON.parse(localStorage.getItem(key)) || {}
  } catch (error) {
    return {}
  }
  return data
}
function getContentTypeFromBase64 (base64Data) {
  const regex = /^data:(.+);base64,/
  const matches = base64Data.match(regex)
  if (matches && matches.length >= 2) {
    return matches[1]
  }
  return null
}
function base64ToBlobFromURL (base64URL, contentType) {
  return fetch(base64URL).then(response => response.blob())
}
const setLocalDataOfWin = (key, value) => {
  localStorage.setItem(key, JSON.stringify(value))
  // window[key] = value
}
async function uploadImage (blob, fileType = '.svg', filename) {
  // const blob = await (await fetch(src)).blob();
  const body = new FormData()
  body.append(
    'image',
    new File([blob], (filename || new Date().getTime()) + fileType)
  )

  const resp = await api.fetchApi('/upload/image', {
    method: 'POST',
    body
  })

  // console.log(resp)
  let data = await resp.json()
  let { name, subfolder } = data
  let src = api.apiURL(
    `/view?filename=${encodeURIComponent(
      name
    )}&type=input&subfolder=${subfolder}${app.getPreviewFormatParam()}${app.getRandParam()}`
  )

  return src
}

function createImage (url) {
  let im = new Image()
  return new Promise((res, rej) => {
    im.onload = () => res(im)
    im.src = url
  })
}

const parseImage = url => {
  return new Promise((res, rej) => {
    fetch(url)
      .then(response => response.blob())
      .then(blob => {
        const reader = new FileReader()
        reader.onloadend = () => {
          const base64data = reader.result
          res(base64data)
          // 在这里可以将base64数据用于进一步处理或显示图片
        }
        reader.readAsDataURL(blob)
      })
      .catch(error => {
        console.log('发生错误:', error)
      })
  })
}

function get_position_style (ctx, widget_width, y, node_height) {
  const MARGIN = 4 // the margin around the html element

  /* Create a transform that deals with all the scrolling and zooming */
  const elRect = ctx.canvas.getBoundingClientRect()
  const transform = new DOMMatrix()
    .scaleSelf(
      elRect.width / ctx.canvas.width,
      elRect.height / ctx.canvas.height
    )
    .multiplySelf(ctx.getTransform())
    .translateSelf(MARGIN, MARGIN + y)

  return {
    transformOrigin: '0 0',
    transform: transform,
    left: `0`,
    top: `0`,
    cursor: 'pointer',
    position: 'absolute',
    maxWidth: `${widget_width - MARGIN * 2}px`,
    // maxHeight: `${node_height - MARGIN * 2}px`, // we're assuming we have the whole height of the node
    width: `${widget_width - MARGIN * 2}px`,
    // height: `${node_height * 0.3 - MARGIN * 2}px`,
    // background: '#EEEEEE',
    display: 'flex',
    flexDirection: 'column',
    // alignItems: 'center',
    justifyContent: 'space-around'
  }
}

async function extractMaterial (
  modelViewerVariants,
  selectMaterial,
  material_img
) {
  // 材质
  const materialsNames = []
  for (
    let index = 0;
    index < modelViewerVariants.model.materials.length;
    index++
  ) {
    let m = modelViewerVariants.model.materials[index]
    let thumbUrl
    try {
      thumbUrl =
        await m.pbrMetallicRoughness.baseColorTexture.texture.source.createThumbnail(
          1024,
          1024
        )
    } catch (error) {}
    if (thumbUrl)
      materialsNames.push({
        value: m.name,
        text: `#${index} ${m.name}`,
        index,
        thumbUrl
      })
  }

  selectMaterial.innerHTML = ''
  material_img.innerHTML = ''

  for (let index = 0; index < materialsNames.length; index++) {
    const name = materialsNames[index]
    const option = document.createElement('option')
    option.value = name.thumbUrl
    option.textContent = name.text
    selectMaterial.appendChild(option)
    let img = new Image()
    img.src = name.thumbUrl
    // img.setAttribute('data-index',name.index)
    img.style.width = '40px'
    material_img.appendChild(img)
    if (index == 0) {
      material_img.setAttribute('src', name.thumbUrl)
    }
  }
}

app.registerExtension({
  name: 'Mixlab.3D.3DImage',
  async getCustomWidgets (app) {
    return {
      THREED (node, inputName, inputData, app) {
        // console.log('##node', node, inputName, inputData)
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 88], // a default size
          draw (ctx, node, width, y) {},
          computeSize (...args) {
            return [128, 88] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            let d = getLocalData('_mixlab_3d_image')
            console.log('serializeValue', node)
            if (d && d[node.id]) {
              let { url, bg, material } = d[node.id]
              let base64 = await parseImage(url)
              let bg_base64 = await parseImage(bg)
              let material_base64 = await parseImage(material)

              return JSON.parse(
                JSON.stringify({
                  image: base64,
                  bg_image: bg_base64,
                  material: material_base64
                })
              )
            } else {
              return {}
            }
          }
        }
        node.addCustomWidget(widget)
        return widget
      }
    }
  },

  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == '3DImage') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = async function () {
        orig_nodeCreated?.apply(this, arguments)

        const uploadWidget = this.widgets.filter(w => w.name == 'upload')[0]

        const widget = {
          type: 'div',
          name: 'upload-preview',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width, 88, node.size[1])
            )
          }
        }

        widget.div = $el('div', {})
        widget.div.style.width = `120px`

        document.body.appendChild(widget.div)

        const inputDiv = (key, placeholder, preview) => {
          let div = document.createElement('div')
          const ip = document.createElement('input')
          ip.type = 'file'
          ip.className = `${'comfy-multiline-input'} ${placeholder}`
          div.style = `display: flex;
            align-items: center; 
            margin: 6px 8px;
            margin-top: 0;`
          ip.placeholder = placeholder
          // ip.value = value

          ip.style = `outline: none;
            border: none;
            padding: 4px;
            width: 60%;cursor: pointer;
            height: 32px;`
          const label = document.createElement('label')
          label.style = 'font-size: 10px;min-width:32px'
          label.innerText = placeholder
          div.appendChild(label)
          div.appendChild(ip)

          let that = this,
            filename = new Date().getTime()

          ip.addEventListener('change', async event => {
            const file = event.target.files[0]
            const reader = new FileReader()
            filename = new Date().getTime()
            // 读取文件内容
            reader.onload = async e => {
              const fileURL = URL.createObjectURL(file)
              // console.log('文件URL: ', fileURL)
              let html = `<model-viewer  src="${fileURL}" 
                min-field-of-view="0deg" max-field-of-view="180deg"
                 shadow-intensity="1" 
                 camera-controls 
                 touch-action="pan-y">
                 
                 <div class="controls">
                  <div>Variant: <select class="variant"></select></div>
                  <div>Material: <select class="material"></select></div>
                  <div>Material: <div class="material_img"> </div></div>
                  <div><button class="bg">BG</button></div>
                </div></model-viewer>`

              preview.innerHTML = html
              if (that.size[1] < 400) {
                that.setSize([that.size[0], that.size[1] + 300])
                app.canvas.draw(true, true)
              }

              const modelViewerVariants = preview.querySelector('model-viewer')
              const select = preview.querySelector('.variant')
              const selectMaterial = preview.querySelector('.material')
              const material_img = preview.querySelector('.material_img')
              const bg = preview.querySelector('.bg')

              if (modelViewerVariants) {
                modelViewerVariants.style.width = `${that.size[0] - 24}px`
                modelViewerVariants.style.height = `${that.size[1] - 48}px`
              }

              modelViewerVariants.addEventListener('load', async () => {
                const names = modelViewerVariants.availableVariants

                // 变量
                for (const name of names) {
                  const option = document.createElement('option')
                  option.value = name
                  option.textContent = name
                  select.appendChild(option)
                }
                // Adds a default option.
                if (names.length === 0) {
                  const option = document.createElement('option')
                  option.value = 'default'
                  option.textContent = 'Default'
                  select.appendChild(option)
                }

                // 材质
                extractMaterial(
                  modelViewerVariants,
                  selectMaterial,
                  material_img
                )
              })

              let timer = null
              const delay = 500 // 延迟时间，单位为毫秒

              async function checkCameraChange () {
                let dd = getLocalData(key)
                let w, h
                let base64Data = modelViewerVariants.toDataURL()

                const contentType = getContentTypeFromBase64(base64Data)

                const blob = await base64ToBlobFromURL(base64Data, contentType)

                //  const fileBlob = new Blob([e.target.result], { type: file.type });
                let url = await uploadImage(blob, '.png')
                // console.log(url)

                //  材质贴图
                let thumbUrl = material_img.getAttribute('src')
                let tb = await base64ToBlobFromURL(thumbUrl)
                let tUrl = await uploadImage(tb, '.png')

                console.log(tUrl)

                if (!dd[that.id]) dd[that.id] = { url, bg: url, material: tUrl }
                dd[that.id] = { ...dd[that.id], url, material: tUrl }

                setLocalDataOfWin(key, dd)
              }

              function startTimer () {
                if (timer) clearTimeout(timer)
                timer = setTimeout(checkCameraChange, delay)
              }

              modelViewerVariants.addEventListener('camera-change', startTimer)

              select.addEventListener('input', event => {
                modelViewerVariants.variantName =
                  event.target.value === 'default' ? null : event.target.value
                // 材质
                extractMaterial(
                  modelViewerVariants,
                  selectMaterial,
                  material_img
                )
                checkCameraChange()
              })

              selectMaterial.addEventListener('input', event => {
                console.log(selectMaterial.value)
                material_img.setAttribute('src', selectMaterial.value)
                checkCameraChange()
              })

              bg.addEventListener('click', () => {
                // 创建一个input元素
                var input = document.createElement('input')
                input.type = 'file'

                // 监听input的change事件
                input.addEventListener('change', function () {
                  // 获取上传的文件
                  var file = input.files[0]

                  // 创建一个FileReader对象来读取文件
                  var reader = new FileReader()

                  // 监听FileReader的load事件
                  reader.addEventListener('load', async () => {
                    let base64 = reader.result
                    // 将读取的文件内容设置为div的背景
                    preview.style.backgroundImage = 'url(' + base64 + ')'

                    const contentType = getContentTypeFromBase64(base64)

                    const blob = await base64ToBlobFromURL(base64, contentType)

                    //  const fileBlob = new Blob([e.target.result], { type: file.type });
                    let bg_url = await uploadImage(blob, '.png')
                    let bg_img = await createImage(base64)

                    let dd = getLocalData(key)
                    // console.log(dd[that.id],bg_url)
                    if (!dd[that.id]) dd[that.id] = { url: '', bg: bg_url }
                    dd[that.id] = {
                      ...dd[that.id],
                      bg: bg_url,
                      bg_w: bg_img.naturalWidth,
                      bg_h: bg_img.naturalHeight
                    }

                    setLocalDataOfWin(key, dd)

                    // 更新尺寸
                    let w = that.size[0] - 24,
                      h = (w * bg_img.naturalHeight) / bg_img.naturalWidth

                    if (modelViewerVariants) {
                      modelViewerVariants.style.width = `${w}px`
                      modelViewerVariants.style.height = `${h}px`
                    }
                    preview.style.width = `${w}px`
                  })

                  // 读取文件
                  reader.readAsDataURL(file)
                })

                // 触发input的点击事件
                input.click()
              })

              uploadWidget.value = await uploadWidget.serializeValue()

              // 更新尺寸
              let dd = getLocalData(key)
              // console.log(dd[that.id],bg_url)
              if (dd[that.id]) {
                const { bg_w, bg_h } = dd[that.id]
                if (bg_h && bg_w) {
                  let w = that.size[0] - 24,
                    h = (w * bg_h) / bg_w

                  if (modelViewerVariants) {
                    modelViewerVariants.style.width = `${w}px`
                    modelViewerVariants.style.height = `${h}px`
                  }
                  preview.style.width = `${w}px`
                }
              }
            }

            // 以文本形式读取文件
            reader.readAsDataURL(file)
          })
          return div
        }

        let preview = document.createElement('div')
        preview.className = 'preview'
        preview.style = `margin-top: 12px;display: flex;
          justify-content: center;
          align-items: center;background-repeat: no-repeat;background-size: contain;`

        let upload = inputDiv('_mixlab_3d_image', '3D Model', preview)

        widget.div.appendChild(upload)
        widget.div.appendChild(preview)
        this.addCustomWidget(widget)

        const onResize = this.onResize
        let that = this
        this.onResize = function () {
          let modelViewerVariants = preview.querySelector('model-viewer')

          // 更新尺寸
          let dd = getLocalData('_mixlab_3d_image')
          // console.log(dd[that.id],bg_url)
          if (dd[that.id]) {
            const { bg_w, bg_h } = dd[that.id]
            if (bg_h && bg_w) {
              let w = that.size[0] - 24,
                h = (w * bg_h) / bg_w

              if (modelViewerVariants) {
                modelViewerVariants.style.width = `${w}px`
                modelViewerVariants.style.height = `${h}px`
              }
              preview.style.width = `${w}px`
            }
          }

          return onResize?.apply(this, arguments)
        }

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          upload.remove()
          preview.remove()
          widget.div.remove()
          return onRemoved?.()
        }

        if (this.onResize) {
          this.onResize(this.size)
        }
        // this.isVirtualNode = true
        this.serialize_widgets = false //需要保存参数
      }

      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        const r = onExecuted?.apply?.(this, arguments)

        
        let material = message.material[0]
        if (material) {
          const { filename, subfolder, type } = material
          let src = api.apiURL(
            `/view?filename=${encodeURIComponent(
              filename
            )}&type=${type}&subfolder=${subfolder}${app.getPreviewFormatParam()}${app.getRandParam()}`
          )
          console.log('Test', this.widgets, src)
        }

        this.onResize?.(this.size)

        return r
      }
    }
  },
  async loadedGraphNode (node, app) {
    // Fires every time a node is constructed
    // You can modify widgets/add handlers/etc here
    const sleep = (t = 1000) => {
      return new Promise((res, rej) => {
        setTimeout(() => res(1), t)
      })
    }
    if (node.type === '3DImage') {
      // await sleep(0)
      let widget = node.widgets.filter(w => w.name === 'upload-preview')[0]

      let dd = getLocalData('_mixlab_3d_image')

      let id = node.id
      // console.log('3dImage load', node.widgets[0], node.widgets)
      if (!dd[id]) return

      let { url, bg } = dd[id]
      if (!url) return
      // let base64 = await parseImage(url)

      let pre = widget.div.querySelector('.preview')
      pre.style.width = `${node.size[0]}px`
      pre.innerHTML = `
        ${url ? `<img src="${url}" style="width:100%"/>` : ''}
        `
      pre.style.backgroundImage = 'url(' + bg + ')'

      const uploadWidget = node.widgets.filter(w => w.name == 'upload')[0]
      uploadWidget.value = await uploadWidget.serializeValue()
    }
  }
})
