import { app } from '../../../scripts/app.js'
// import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'

async function getConfig () {
  let api_host = `${window.location.hostname}:${window.location.port}`
  let api_base = ''
  let url = `${window.location.protocol}//${api_host}${api_base}`

  const res = await fetch(`${url}/mixlab`, {
    method: 'POST'
  })
  return await res.json()
}

if (!window._mixlab_screen_prompt)
  window._mixlab_screen_prompt =
    'beautiful scenery nature glass bottle landscape,under water'

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
    height: `${node_height * 0.3 - MARGIN * 2}px`,
    background: '#EEEEEE',
    display: 'flex',
    flexDirection: 'column',
    // alignItems: 'center',
    justifyContent: 'space-around'
  }
}

app.registerExtension({
  name: 'Mixlab.image.LoadImagesFromPath',
  async getCustomWidgets (app) {
    return {
      WATCHER (node, inputName, inputData, app) {
        // console.log('node', inputName, inputData[0])
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 24], // a default size
          draw (ctx, node, width, y) {
            // // 绘制文件图标的函数
            // function drawFileIcon () {
            //   // 清空画布
            //   // ctx.clearRect(0, 0, canvas.width, canvas.height)

            //   // 绘制文件外框
            //   ctx.fillStyle = '#000'
            //   ctx.fillRect(5, 5, 40, 40)

            //   // 绘制文件夹图标
            //   ctx.fillStyle = '#f00'
            //   ctx.fillRect(10, 15, 30, 20)

            //   // 绘制监听符号
            //   ctx.beginPath()
            //   ctx.arc(30, 35, 5, 0, 2 * Math.PI)
            //   ctx.fillStyle = '#00f'
            //   ctx.fill()
            // }

            // // 调用绘制函数
            // drawFileIcon()
          },
          computeSize (...args) {
            return [128, 24] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            return window._mixlab_file_path_watcher || ''
          }
        }
        //  widget.something = something;          // maybe adds stuff to it
        node.addCustomWidget(widget) // adds it to the node
        return widget // and returns it.
      },
      PROMPT (node, inputName, inputData, app) {
        // console.log('node', inputName, inputData[0])
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 24], // a default size
          draw (ctx, node, width, y) {
            // a method to draw the widget (ctx is a CanvasRenderingContext2D)
          },
          computeSize (...args) {
            return [128, 24] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            return window._mixlab_screen_prompt || ''
          }
        }
        //  widget.something = something;          // maybe adds stuff to it
        node.addCustomWidget(widget) // adds it to the node
        return widget // and returns it.
      }
    }
  },
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    // console.log(nodeType.comfyClass)
    if (nodeType.comfyClass == 'LoadImagesFromPath') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)

        console.log('watch widtget', this.widgets)

        const watcher = this.widgets.filter(w => w.name == 'watcher')[0]

        watcher.callback = () => {
          if (watcher.value === 'enable') {
            if (window._mixlab_watcher_t)
              clearInterval(window._mixlab_watcher_t)
            window._mixlab_watcher_t = setInterval(() => {
              // 上次路径填充
              getConfig().then(json => {
                console.log(json.event_type)
                if (json.event_type != window._mixlab_file_path_watcher) {
                  window._mixlab_file_path_watcher = json.event_type
                  // widget.card.innerText = window._mixlab_file_path_watcher || ''
                  //运行
                  document.querySelector('#queue-button').click()
                }
              })
            }, 1000)
          } else {
            if (window._mixlab_watcher_t) {
              clearInterval(window._mixlab_watcher_t)
            }
            window._mixlab_watcher_t = null
          }
        }

        // 上次路径填充
        getConfig().then(json => {
          let w = this.widgets.filter(w => w.name == 'file_path')[0]
          if (w) {
            w.value = json.folder_path || ''
          }
          // console.log(json.event_type)
          window._mixlab_file_path_watcher = json.event_type
        })

        /*
                Add the widget, make sure we clean up nicely, and we do not want to be serialized!
                */
        // this.addCustomWidget(widget)
        this.onRemoved = function () {
          // widget.card.remove()
        }
        this.serialize_widgets = true
      }
    }
  }
})
