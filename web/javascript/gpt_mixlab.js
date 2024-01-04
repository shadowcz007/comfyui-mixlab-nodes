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

const getLocalData = key => {
  let data = {}
  try {
    data = JSON.parse(localStorage.getItem(key)) || {}
  } catch (error) {
    return {}
  }
  return data
}

app.registerExtension({
  name: 'Mixlab.GPT.ChatGPTOpenAI',
  async getCustomWidgets (app) {
    return {
      KEY (node, inputName, inputData, app) {
        console.log('##inputData', inputData)
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 32], // a default size
          draw (ctx, node, width, y) {},
          computeSize (...args) {
            return [128,32] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            let data = getLocalData('_mixlab_api_key')
            return data[node.id] || 'by Mixlab'
          }
        }
        //  widget.something = something;          // maybe adds stuff to it
        node.addCustomWidget(widget) // adds it to the node
        return widget // and returns it.
      },
      URL (node, inputName, inputData, app) {
        // console.log('node', inputName, inputData[0])
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 32], // a default size
          draw (ctx, node, width, y) {
            // a method to draw the widget (ctx is a CanvasRenderingContext2D)
          },
          computeSize (...args) {
            return [128, 32] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            let data = getLocalData('_mixlab_api_url')
            return data[node.id] || 'https://api.openai.com/v1'
          }
        }
        //  widget.something = something;          // maybe adds stuff to it
        node.addCustomWidget(widget) // adds it to the node
        return widget // and returns it.
      }
    }
  },

  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'ChatGPTOpenAI') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)

        const api_key = this.widgets.filter(w => w.name == 'api_key')[0]
        const api_url = this.widgets.filter(w => w.name == 'api_url')[0]

        console.log('ChatGPTOpenAI nodeData', this.widgets)

        const widget = {
          type: 'div',
          name: 'chatgptdiv',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width, api_key.y, node.size[1])
            )
          }
        }

        widget.div = $el('div', {})

        document.body.appendChild(widget.div)

        const inputDiv = (key, placeholder) => {
          let div = document.createElement('div')
          const ip = document.createElement('input')
          ip.type = placeholder === 'Key' ? 'password' : 'text'
          ip.className = `${'comfy-multiline-input'} ${placeholder}`
          div.style = `display: flex;
          align-items: center; 
          margin: 6px 8px;
          margin-top: 0;`
          ip.placeholder = placeholder
          ip.value = placeholder

          ip.style = `margin-left: 24px;
          outline: none;
          border: none;
          padding: 4px;width: 100%;`
          const label = document.createElement('label')
          label.style = 'font-size: 10px;min-width:32px'
          label.innerText = placeholder
          div.appendChild(label)
          div.appendChild(ip)

          ip.addEventListener('change', () => {
            let data = getLocalData(key)
            data[this.id] = ip.value.trim()
            localStorage.setItem(key, JSON.stringify(data))
            console.log(this.id, key)
          })
          return div
        }

        let inputKey = inputDiv('_mixlab_api_key', 'Key')
        let inputUrl = inputDiv('_mixlab_api_url', 'URL')

        widget.div.appendChild(inputKey)
        widget.div.appendChild(inputUrl)

        this.addCustomWidget(widget)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          inputUrl.remove()
          inputKey.remove()
          widget.div.remove()
          return onRemoved?.()
        }

        this.serialize_widgets = true //需要保存参数
      }
    }
  },
  async loadedGraphNode (node, app) {
    // Fires every time a node is constructed
    // You can modify widgets/add handlers/etc here

    if (node.type === 'ChatGPTOpenAI') {
      let widget = node.widgets.filter(w => w.div)[0]

      let apiKey = getLocalData('_mixlab_api_key'),
        url = getLocalData('_mixlab_api_url')

      let id = node.id

      // console.log('ChatGPTOpenAI serialize_widgets', this)

      widget.div.querySelector('.Key').value = apiKey[id] || 'by Mixlab'
      widget.div.querySelector('.URL').value =
        url[id] || 'https://api.openai.com/v1'
    }
  }
})

app.registerExtension({
  name: 'Mixlab.GPT.ShowTextForGPT',
  async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if (nodeData.name === "ShowTextForGPT") {
			function populate(text) {
				if (this.widgets) {
          
					const pos = this.widgets.findIndex((w) => w.name === "text");
					if (pos !== -1) {
						for (let i = pos; i < this.widgets.length; i++) {
							this.widgets[i].onRemove?.();
						}
						this.widgets.length = pos;
					}
				}
        // console.log('ShowTextForGPT',text)
				for (let list of text) {
					const w = ComfyWidgets["STRING"](this, "text", ["STRING", { multiline: true }], app).widget;
					w.inputEl.readOnly = true;
					w.inputEl.style.opacity = 0.6;

          try {
            let data=JSON.parse(list);
            data=Array.from(data,d=>{
              return {
                ...d,
                content:decodeURIComponent(d.content)
              }
            })
            list=JSON.stringify(data,null,2)
          } catch (error) {
            // console.log(error)
          }

					w.value =list;
        
				}
        // console.log('ShowTextForGPT',this.widgets.length)
				requestAnimationFrame(() => {
					const sz = this.computeSize();
					if (sz[0] < this.size[0]) {
						sz[0] = this.size[0];
					}
					if (sz[1] < this.size[1]) {
						sz[1] = this.size[1];
					}
					this.onResize?.(sz);
					app.graph.setDirtyCanvas(true, false);
				});
			}

			// When the node is executed we will be sent the input text, display this in the widget
			const onExecuted = nodeType.prototype.onExecuted;
			nodeType.prototype.onExecuted = function (message) {
				onExecuted?.apply(this, arguments);
        console.log('##',message.text)
				populate.call(this, message.text);
			};

			const onConfigure = nodeType.prototype.onConfigure;
			nodeType.prototype.onConfigure = function () {
				onConfigure?.apply(this, arguments);
				if (this.widgets_values?.length) {
          
					populate.call(this, this.widgets_values);
				}
			};

      this.serialize_widgets = true //需要保存参数

		}


	},
})
