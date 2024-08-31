import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { $el } from '../../../scripts/ui.js'

import { loadExternalScript, get_position_style } from './common.js'

function setCameraOrbit (modelview, distant, angles, screenNumber) {
  //2.1 20
  // const angles = {
  //   1: -20.0,
  //   2: -17.9,
  //   3: -15.8,
  //   4: -13.7,
  //   5: -11.6,
  //   6: -9.5,
  //   7: -7.4,
  //   8: -5.3,
  //   9: -3.2,
  //   10: -1.1,
  //   11: 1.1,
  //   12: 3.2,
  //   13: 5.3,
  //   14: 7.4,
  //   15: 9.5,
  //   16: 11.6,
  //   17: 13.7,
  //   18: 15.8,
  //   19: 17.9,
  //   20: 20.0
  // };

  // 12 3.6
  // const angles = {
  //   1: -20.0,
  //   2: -16.4,
  //   3: -12.7,
  //   4: -9.1,
  //   5: -5.5,
  //   6: -1.8,
  //   7: 1.8,
  //   8: 5.5,
  //   9: 9.1,
  //   10: 12.7,
  //   11: 16.4,
  //   12: 20.0
  // }

  const angle = angles[screenNumber]

  let co=modelview.cameraOrbit.split(" ")

  if (angle !== undefined) {
    
    modelview.cameraOrbit = `${angle}deg ${co[1]} ${distant}m`
    console.log(screenNumber, angle)
  } else {
    console.error('Invalid screen number')
  }
}

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

async function uploadImage_ (blob, fileType = '.svg', filename) {
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
  return data
}

async function uploadImage (blob, fileType = '.svg', filename) {
  let data = await uploadImage_(blob, fileType, filename)
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
    option.setAttribute('data-index', index)
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

async function changeMaterial (
  modelViewerVariants,
  targetMaterial,
  newImageUrl
) {
  const targetTexture = await modelViewerVariants.createTexture(newImageUrl)
  // 用图片创建纹理
  targetMaterial.pbrMetallicRoughness.baseColorTexture.setTexture(targetTexture)
}

function inputFileClick (isFileURL = false, isGlb = false) {
  return new Promise((res, rej) => {
    // 创建一个input元素
    var input = document.createElement('input')
    input.type = 'file'
    input.accept = isGlb ? '.glb' : 'image/*'

    // 监听input的change事件
    input.addEventListener('change', function () {
      // 获取上传的文件
      var file = input.files[0]

      if (isFileURL) {
        res(URL.createObjectURL(file))
        return
      }

      // 创建一个FileReader对象来读取文件
      var reader = new FileReader()

      // 监听FileReader的load事件
      reader.addEventListener('load', async () => {
        let base64 = reader.result
        input.remove()
        res(base64)
      })

      // 读取文件
      reader.readAsDataURL(file)
    })

    // 触发input的点击事件
    input.click()
  })
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
            // console.log('serializeValue', node)
            if (d && d[node.id]) {
              let { url, bg, material, images } = d[node.id]
              let data = {}
              if (url) {
                data.image = await parseImage(url)
              }
              if (bg) {
                data.bg_image = await parseImage(bg)
                if (!data.bg_image.match('data:image/')) {
                  delete data.bg_image
                }
              }

              if (material) {
                data.material = await parseImage(material)
              }

              if (images) {
                data.images = images
              }

              return JSON.parse(JSON.stringify(data))
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

  async init () {
    await loadExternalScript('/mixlab/app/lib/model-viewer.min.js', 'module')
  },

  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == '3DImage') {
      console.log('nodeType.comfyClass', nodeType.comfyClass)
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
              get_position_style(ctx, widget_width - 122, 88, node.size[1], 44)
            )
          }
        }

        widget.div = $el('div', {})
        widget.div.style.width = `120px`
        document.body.appendChild(widget.div)

        const inputDiv = (key, placeholder, preview) => {
          let div = document.createElement('div')
          const ip = document.createElement('button')
          ip.className = `${'comfy-multiline-input'} ${placeholder}`
          div.style = `display: flex;
            align-items: center; 
            margin: 6px 8px;
            margin-top: 0;`

          ip.style = `outline: none;
            border: none;
            padding: 4px;
            width: 100px;cursor: pointer;
            height: 32px;`
          ip.innerText = placeholder
          div.appendChild(ip)

          let that = this

          ip.addEventListener('click', async event => {
            let fileURL = await inputFileClick(true, true)

            // console.log('文件URL: ', fileURL)
            let html = `<model-viewer  src="${fileURL}" 
                oncontextmenu="return false;"
                style="outline:1px solid white"
                min-field-of-view="0deg" 
                max-field-of-view="180deg"
                min-camera-orbit="auto auto 0m"
                max-camera-orbit="auto auto 1000m"
                 shadow-intensity="1" 
                 camera-controls 
                 touch-action="pan-y">
                 
                 <div class="controls">
                  <div>Variant: <select class="variant"></select></div>
                  <div>Material: <select class="material"></select></div>
                  <div>Material: <div class="material_img"> </div></div>
                  <div>
                    <button class="bg">BG</button>
                   
                  </div>
                  <div>
                   <input class="ddcap_distant" type="number" min="1" step="1" value="55">
                   <input class="total_images" type="number" min="1" max="180" step="1" value="20">
                   <input class="ddcap_range" type="number" min="0" max="20" step="0.1" value="2.1"> 
                  <button class="ddcap">Capture Rotational Screenshots</button></div>
                  
                  <div><button class="export">Export GLB</button></div>
                  
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

            const exportGLB = preview.querySelector('.export')

            const ddcap_distant = preview.querySelector('.ddcap_distant')
            const total_images = preview.querySelector('.total_images')
            const ddcap_range = preview.querySelector('.ddcap_range')
            const ddCap = preview.querySelector('.ddcap')
            const sleep = (t = 1000) => {
              return new Promise((res, rej) => {
                return setTimeout(() => {
                  res(t)
                }, t)
              })
            }

            async function captureImage (isUrl = true) {
              let base64Data = modelViewerVariants.toDataURL()

              const contentType = getContentTypeFromBase64(base64Data)

              const blob = await base64ToBlobFromURL(base64Data, contentType)

              if (isUrl) return await uploadImage(blob, '.png')
              return await uploadImage_(blob, '.png')
            }

            async function captureImages (
              ddcap_range = 1,
              total_images = 12,
              distant = 0.23
            ) {
              //  初始 角度
              var center = modelViewerVariants.getBoundingBoxCenter().toString()
              modelViewerVariants.cameraTarget = center

              const startAngle = -((total_images - 1) / 2) * ddcap_range
              const angles = {}

              for (let i = 0; i < total_images; i++) {
                angles[i + 1] = startAngle + i * ddcap_range
              }
              console.log(angles)

              let frames = []

              modelViewerVariants.removeAttribute('camera-controls')

              for (let i = 0; i < total_images; i++) {
                setCameraOrbit(modelViewerVariants, distant, angles, i + 1)

                // modelViewerVariants.cameraOrbit = `${currentAngle}deg ${initialCameraOrbit[1]} ${initialCameraOrbit[2]}`
                await sleep(1000)
                // console.log(`Capturing image at angle: ${currentAngle}deg`)
                let file = await captureImage(false)
                frames.push(file)
                // currentAngle += angleIncrement
              }
              await sleep(1000)
              // 恢复到初始旋转角度
              // modelViewerVariants.cameraOrbit = initialCameraOrbit.join(' ')
              modelViewerVariants.setAttribute('camera-controls', '')
              return frames
            }

            ddCap.addEventListener('click', async e => {
              const distant = Number(ddcap_distant.value), //  23m
                totalImages = Number(total_images.value),
                angleIncrement = Number(ddcap_range.value)
              console.log(angleIncrement, totalImages)
              let images = await captureImages(
                angleIncrement,
                totalImages,
                distant
              )

              let dd = getLocalData(key)
              dd[that.id].images = images
              setLocalDataOfWin(key, dd)
            })

            ddcap_distant.addEventListener('input', async e => {
              // console.log(ddcap_distant.value)
              const center = modelViewerVariants.getBoundingBoxCenter().toString()
              modelViewerVariants.cameraTarget = center;
              const initialCameraOrbit =
                modelViewerVariants.cameraOrbit.split(' ')
              modelViewerVariants.cameraOrbit = `${initialCameraOrbit[2]} ${initialCameraOrbit[1]} ${ddcap_distant.value}m`
              modelViewerVariants.setAttribute('camera-controls', '')
            })

            // ddcap_range_top.addEventListener('input', async e => {
            //   // console.log(ddcap_range.value)
            //   const initialCameraOrbit =
            //     modelViewerVariants.cameraOrbit.split(' ')
            //   modelViewerVariants.cameraOrbit = `${initialCameraOrbit[0]} ${ddcap_range_top.value}deg ${initialCameraOrbit[2]}`
            //   modelViewerVariants.setAttribute('camera-controls', '')
            // })

            if (modelViewerVariants) {
              modelViewerVariants.style.width = `${that.size[0] - 48}px`
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
              extractMaterial(modelViewerVariants, selectMaterial, material_img)
            })

            let timer = null
            const delay = 500 // 延迟时间，单位为毫秒

            async function checkCameraChange () {
              let dd = getLocalData(key)

              //  const fileBlob = new Blob([e.target.result], { type: file.type });
              let url = await captureImage()

              let bg_blob = await base64ToBlobFromURL(
                'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mN88uXrPQAFwwK/6xJ6CQAAAABJRU5ErkJggg=='
              )
              let url_bg = await uploadImage(bg_blob, '.png')
              // console.log('url_bg',url_bg)

              if (!dd[that.id]) {
                dd[that.id] = { url, bg: url_bg }
              } else {
                dd[that.id] = { ...dd[that.id], url }
              }

              //  材质贴图
              let thumbUrl = material_img.getAttribute('src')
              if (thumbUrl) {
                let tb = await base64ToBlobFromURL(thumbUrl)
                let tUrl = await uploadImage(tb, '.png')
                // console.log('材质贴图', tUrl, thumbUrl)
                dd[that.id].material = tUrl
              }

              setLocalDataOfWin(key, dd)
            }

            function startTimer () {
              if (timer) clearTimeout(timer)
              timer = setTimeout(checkCameraChange, delay)
            }

            modelViewerVariants.addEventListener('camera-change', startTimer)

            select.addEventListener('input', async event => {
              modelViewerVariants.variantName =
                event.target.value === 'default' ? null : event.target.value
              // 材质
              await extractMaterial(
                modelViewerVariants,
                selectMaterial,
                material_img
              )
              checkCameraChange()
            })

            selectMaterial.addEventListener('input', event => {
              // console.log(selectMaterial.value)
              material_img.setAttribute('src', selectMaterial.value)

              if (selectMaterial.getAttribute('data-new-material')) {
                let index =
                  ~~selectMaterial.selectedOptions[0].getAttribute('data-index')
                changeMaterial(
                  modelViewerVariants,
                  modelViewerVariants.model.materials[index],
                  selectMaterial.getAttribute('data-new-material')
                )
              }

              checkCameraChange()
            })

            //更新bg
            const updateBgData = (id, key, url, w, h) => {
              let dd = getLocalData(key)
              // console.log(dd[that.id],url)
              if (!dd[id]) dd[id] = { url: '', bg: url }
              dd[id] = {
                ...dd[id],
                bg: url,
                bg_w: w,
                bg_h: h
              }
              setLocalDataOfWin(key, dd)
            }

            bg.addEventListener('click', async () => {
              //更新bg
              updateBgData(that.id, key, '', 0, 0)
              preview.style.backgroundImage = 'none'

              let base64 = await inputFileClick(false, false)
              // 将读取的文件内容设置为div的背景
              preview.style.backgroundImage = 'url(' + base64 + ')'

              const contentType = getContentTypeFromBase64(base64)

              const blob = await base64ToBlobFromURL(base64, contentType)

              //  const fileBlob = new Blob([e.target.result], { type: file.type });
              let bg_url = await uploadImage(blob, '.png')
              let bg_img = await createImage(base64)

              //更新bg
              updateBgData(
                that.id,
                key,
                bg_url,
                bg_img.naturalWidth,
                bg_img.naturalHeight
              )

              // 更新尺寸
              let w = that.size[0] - 128,
                h = (w * bg_img.naturalHeight) / bg_img.naturalWidth

              if (modelViewerVariants) {
                modelViewerVariants.style.width = `${w}px`
                modelViewerVariants.style.height = `${h}px`
              }
              preview.style.width = `${w}px`
            })

            exportGLB.addEventListener('click', async () => {
              const glTF = await modelViewerVariants.exportScene()
              const file = new File([glTF], 'export.glb')
              const link = document.createElement('a')
              link.download = file.name
              link.href = URL.createObjectURL(file)
              link.click()
            })

            uploadWidget.value = await uploadWidget.serializeValue()

            // 更新尺寸
            let dd = getLocalData(key)
            // console.log(dd[that.id],bg_url)
            if (dd[that.id]) {
              const { bg_w, bg_h } = dd[that.id]
              if (bg_h && bg_w) {
                let w = that.size[0] - 48,
                  h = (w * bg_h) / bg_w

                if (modelViewerVariants) {
                  modelViewerVariants.style.width = `${w}px`
                  modelViewerVariants.style.height = `${h}px`
                }
                preview.style.width = `${w}px`
              }
            }
          })
          return div
        }

        let preview = document.createElement('div')
        preview.className = 'preview'
        preview.style = `margin-top: 12px;
          display: flex;
          justify-content: center;
          align-items: center;background-repeat: no-repeat;
          background-size: contain;`

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

          if (dd[that.id]) {
            const { bg_w, bg_h } = dd[that.id]
            let w = that.size[0] - 128
            preview.style.width = `${w}px`
            console.log('更新尺寸', w)

            if (modelViewerVariants) {
              modelViewerVariants.style.width = `${w}px`
              modelViewerVariants.style.height = `${Math.round(
                that.size[1] * 0.8
              )}px`
            }

            if (bg_h && bg_w) {
              let h = (w * bg_h) / bg_w
              if (modelViewerVariants) {
                modelViewerVariants.style.height = `${h}px`
              }
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

        let div = this.widgets.filter(d => d.div)[0]?.div
        // console.log('Test', this.widgets)

        let material = message.material[0]
        if (material) {
          const { filename, subfolder, type } = material
          let src = api.apiURL(
            `/view?filename=${encodeURIComponent(
              filename
            )}&type=${type}&subfolder=${subfolder}${app.getPreviewFormatParam()}${app.getRandParam()}`
          )

          const modelViewerVariants = div.querySelector('model-viewer')

          const selectMaterial = div.querySelector('.material')

          let index =
            ~~selectMaterial.selectedOptions[0].getAttribute('data-index')

          selectMaterial.setAttribute('data-new-material', src)

          changeMaterial(
            modelViewerVariants,
            modelViewerVariants.model.materials[index],
            src
          )
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
      pre.style.width = `${node.size[0] - 24}px`
      pre.innerHTML = `
        ${url ? `<img src="${url}" style="width:100%"/>` : ''}
        `
      pre.style.backgroundImage = 'url(' + bg + ')'

      const uploadWidget = node.widgets.filter(w => w.name == 'upload')[0]
      uploadWidget.value = await uploadWidget.serializeValue()
    }
  }
})
