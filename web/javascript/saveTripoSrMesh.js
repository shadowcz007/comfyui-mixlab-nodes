import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { $el } from '../../../scripts/ui.js'


function get_position_style (ctx, widget_width, y, node_height) {
  const MARGIN = 14 // the margin around the html element

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
    // outline: '1px solid red',
    display: 'flex',
    flexDirection: 'column',
    // alignItems: 'center',
    justifyContent: 'space-around'
  }
}


app.registerExtension({
  name: 'Mixlab.3D.SaveTripoSRMesh',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'SaveTripoSRMesh') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = async function () {
        orig_nodeCreated?.apply(this, arguments)

        const widget = {
          type: 'div',
          name: 'preview',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width, 88, node.size[1])
            )
          }
          //   value: [],
          //   async serializeValue (nodeId, widgetIndex) {
          //     return widget.value
          //   }
        }

        widget.div = $el('div', {})
        widget.div.style.width = `120px`

        document.body.appendChild(widget.div)

        // preview.style = `margin-top: 12px;display: flex;
        //   justify-content: center;
        //   align-items: center;background-repeat: no-repeat;background-size: contain;`

        this.addCustomWidget(widget)

        const onResize = this.onResize
        this.onResize = () => {
          widget.div.style.width = `${this.size[0]}px`
          widget.div.style.height = `${this.size[1] - 112}px`
          let mvs = widget.div.querySelectorAll('model-viewer')
          for (const m of mvs) {
            m.style.height = `${Math.round(
              (this.size[1] - 112) / mvs.length
            )}px`
            // console.log(m.style.height)
          }
          //   console.log('resize', this.size)
          return onResize?.apply(this, arguments)
        }

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
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

        let widget = this.widgets.filter(d => d.name == 'preview')[0]
        console.log('Test', widget, message)

        let meshes = message.mesh
        widget.div.innerHTML = ''

        for (const mesh of meshes) {
          if (mesh) {
            const { filename, subfolder, type } = mesh
            const fileURL = api.apiURL(
              `/view?filename=${encodeURIComponent(
                filename
              )}&type=${type}&subfolder=${subfolder}${app.getPreviewFormatParam()}${app.getRandParam()}`
            )

            let modelViewer = document.createElement('div')
            modelViewer.innerHTML = `<model-viewer  src="${fileURL}" 
              min-field-of-view="0deg" max-field-of-view="180deg"
              shadow-intensity="1" 
              camera-controls 
              touch-action="pan-y"
                  style="width:100%;margin:4px;min-height:88px"
              >
              
              <div class="controls">
            
              <div><button class="export" style="
              background-color: var(--comfy-input-bg);
              border-radius: 8px;
              border-color: var(--border-color);
              border-style: solid;
              color: var(--descrip-text);cursor: pointer;">Export GLB</button></div>
              
              </div></model-viewer>`
            widget.div.appendChild(modelViewer)
            let modelViewerVariants= modelViewer
            .querySelector('model-viewer');
            
            modelViewer
              .querySelector('.export')
              .addEventListener('click', async e => {
                e.preventDefault()
                const glTF = await modelViewerVariants.exportScene()
                const file = new File([glTF], filename)
                const link = document.createElement('a')
                link.download = file.name
                link.href = URL.createObjectURL(file)
                link.click()
              })
          }
        }

        // widget.value = [meshes]

        this.onResize?.(this.size)

        return r
      }
    }
  },
  async loadedGraphNode (node, app) {
    const sleep = (t = 1000) => {
      return new Promise((res, rej) => {
        setTimeout(() => res(1), t)
      })
    }
    // if (node.type === 'SaveTripoSRMesh') {
    //   await sleep(0)
    //   let widget = node.widgets.filter(w => w.name === 'preview')[0]
    //   widget.div.innerHTML = ''

    //   for (const mesh of widget.value) {
    //     if (mesh) {
    //       const { filename, subfolder, type } = mesh
    //       const fileURL = api.apiURL(
    //         `/view?filename=${encodeURIComponent(
    //           filename
    //         )}&type=${type}&subfolder=${subfolder}${app.getPreviewFormatParam()}${app.getRandParam()}`
    //       )

    //       let modelViewer = document.createElement('div')
    //       modelViewer.innerHTML = `<model-viewer  src="${fileURL}"
    // 	 min-field-of-view="0deg" max-field-of-view="180deg"
    // 	 shadow-intensity="1"
    // 	 camera-controls
    // 	 touch-action="pan-y">

    // 	 <div class="controls">

    // 	  <div><button class="export">Export GLB</button></div>

    // 	</div></model-viewer>`
    //       widget.div.appendChild(modelViewer)
    //     }
    //   }
    // }
  }
})
