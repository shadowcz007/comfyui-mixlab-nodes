import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'

function deepEqual (obj1, obj2) {
  if (typeof obj1 !== typeof obj2) {
    return false
  }

  if (typeof obj1 !== 'object' || obj1 === null || obj2 === null) {
    return obj1 === obj2
  }

  const keys1 = Object.keys(obj1)
  const keys2 = Object.keys(obj2)

  if (keys1.length !== keys2.length) {
    return false
  }

  for (let key of keys1) {
    if (!deepEqual(obj1[key], obj2[key])) {
      return false
    }
  }

  return true
}

async function get_nodes_map () {
  let api_host = `${window.location.hostname}:${window.location.port}`
  let api_base = ''
  let url = `${window.location.protocol}//${api_host}${api_base}`

  const res = await fetch(`${url}/mixlab/nodes_map`, {
    method: 'POST',
    body: JSON.stringify({
      data: 'json'
    })
  })
  return await res.json()
}

function injectCSS (css) {
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

injectCSS(`::-webkit-scrollbar {
  width: 2px;
}

@keyframes loading_mixlab {
  0% {
    background-color: green;
  }

  50% {
    background-color: lightgreen;
  }

  100% {
    background-color: green;
  }
}

.loading_mixlab {
  background-color: green;
  animation-name: loading_mixlab;
  animation-duration: 2s;
  animation-iteration-count: infinite;
}`)

async function getCustomnodeMappings (mode = 'url') {
  // mode = "local";
  let api_host = `${window.location.hostname}:${window.location.port}`
  let api_base = ''
  let url = `${window.location.protocol}//${api_host}${api_base}`

  let nodes = {}
  try {
    const response = await fetch(`${url}/customnode/getmappings?mode=${mode}`)
    const data = await response.json()
    for (let url in data) {
      let n = data[url]
      for (let node of n[0]) {
        // if(node=='CLIPSeg')console.log('#CLIPSeg',n)
        nodes[node] = { url, title: n[1].title_aux }
      }
    }
  } catch (error) {
    const data = (await get_nodes_map()).data

    for (let url in data) {
      let n = data[url]
      for (let node of n[0]) {
        // if(node=='CLIPSeg')console.log('#CLIPSeg',n)
        nodes[node] = { url, title: n[1].title_aux }
      }
    }
  }

  return nodes
}

const missingNodeGithub = (missingNodeTypes, nodesMap) => {
  let ts = {}

  Array.from(new Set(missingNodeTypes), n => {
    if (nodesMap[n]) {
      let title = nodesMap[n].title
      if (!ts[title]) {
        ts[title] = {
          title,
          nodes: {},
          url: nodesMap[n].url
        }
      }
      ts[title].nodes[n] = 1
    } else {
      ts[n] = {
        title: n,
        nodes: {},
        url: `https://github.com/search?q=${n}&type=code`
      }
      ts[n].nodes[n] = 1
    }
  })

  return Array.from(Object.values(ts), n => {
    const url = n.url
    return `<li style="color: white;
   background: black;
   padding: 8px;
   font-size: 12px;">${n.title}<a href="${url}" target="_blank"> 🔗</a></li>`
  })
}

let nodesMap

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

app.showMissingNodesError = async function (
  missingNodeTypes,
  hasAddedNodes = true
) {
  nodesMap =
    nodesMap && Object.keys(nodesMap).length > 0
      ? nodesMap
      : await getCustomnodeMappings('url')

  // console.log('#nodesMap', nodesMap)
  // console.log('###MIXLAB', missingNodeTypes, hasAddedNodes)
  this.ui.dialog.show(
    `When loading the graph, the following node types were not found: <ul>${missingNodeGithub(
      missingNodeTypes,
      nodesMap
    ).join('')}</ul>${
      hasAddedNodes
        ? 'Nodes that have failed to load will show as red on the graph.'
        : ''
    }`
  )
  this.logging.addEntry('Comfy.App', 'warn', {
    MissingNodes: missingNodeTypes
  })
}

// app.registerExtension({
//   name: 'Comfy.MDNote',
//   registerCustomNodes () {
//     class NoteNode {
//       // color = LGraphCanvas.node_colors.yellow.color
//       // bgcolor = LGraphCanvas.node_colors.yellow.bgcolor
//       // groupcolor = LGraphCanvas.node_colors.yellow.groupcolor
//       constructor () {
//         if (!this.properties) {
//           this.properties = {}
//           this.properties.text = ''
//         }
//         console.log('NoteNode1', this)

//         const widget = {
//           type: 'div',
//           name: 'input_color',
//           draw (ctx, node, widget_width, y, widget_height) {
//             Object.assign(
//               this.div.style,
//               get_position_style(
//                 ctx,
//                 widget_width,
//                 44,
//                 node.size[1]
//               )
//             )
//           }
//         }

//         widget.div = $el('div', {});
//         widget.div.innerText='1111'

//         document.body.appendChild(widget.div)

//         this.addCustomWidget(widget)

//         this.serialize_widgets = true
//         this.isVirtualNode = true
//       }
//     }

//     // Load default visibility

//     LiteGraph.registerNodeType(
//       'MDNote',
//       Object.assign(NoteNode, {
//         title_mode: LiteGraph.NORMAL_TITLE,
//         title: 'MDNote',
//         collapsable: true
//       })
//     )

//     NoteNode.category = '♾️Mixlab/utils'
//   },

// })

async function fetchReadmeContent (url) {
  try {
    // var repo = 'owner/repo'; // 仓库的拥有者和名称
    var match = url.match(/github.com\/([^/]+\/[^/]+)/)
    var repo = match[1]
    var url = `https://api.github.com/repos/${repo}/readme`
    var response = await fetch(url)
    var data = await response.json()
    var readmeUrl = data.download_url

    var readmeResponse = await fetch(readmeUrl)
    var content = await readmeResponse.text()
    console.log(content) // 在控制台输出readme.md文件的内容

    return content
  } catch (error) {
    console.log('获取readme.md文件信息失败:', error)
  }
}

function createModal (url, markdown) {
  // Create modal element
  var div =
    document.querySelector('#mix-modal') || document.createElement('div')
  div.id = 'mix-modal'
  div.innerHTML = ''

  div.style.cssText = `width: 100%;
  z-index: 9990;
  height: 100vh;display: flex;
  color: var(--descrip-text);
  background-color: var(--comfy-menu-bg);
  position: fixed;
  top: 0;
  left: 0;
}
  `

  var modal = document.createElement('div')

  div.appendChild(modal)

  // Set modal styles
  modal.style.cssText = `
    background: white;
    height: 80vh;
    overflow-y: scroll;
    overflow-x: hidden;
    padding: 24px;
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 9999;
  `

  // Create modal content area
  var modalContent = document.createElement('div')
  modalContent.classList.add('modal-content')

  // Create close button
  var closeButton = document.createElement('span')
  closeButton.classList.add('close')
  closeButton.innerHTML = '&times;'

  // Set close button styles
  closeButton.style.cssText = `
  color: var(--input-text);
  background-color: var(--comfy-input-bg);
  border-color: var(--border-color);
padding: 4px;
/* border-radius: 50%; */
position: fixed;
top: 8px;
right: 8px;
cursor: pointer;
width: 32px;
height: 32px;
display: flex;
justify-content: center;
align-items: center;
`

  // Set modal content area styles
  modalContent.style.cssText = `
position: relative;
`
  // Click event to close the modal
  closeButton.onclick = function () {
    div.style.display = 'none'
  }

  // Append close button to modal content area
  modalContent.appendChild(closeButton)

  // Create element for displaying Markdown content
  var markdownContent = document.createElement('div')
  markdownContent.classList.add('markdown-content')

  var converter = new showdown.Converter()
  var html = converter.makeHtml(markdown)

  // Hide images in the markdown when they fail to load
  var regex = /<img[^>]+src="?([^"\s]+)"?[^>]*>/g
  html = html.replace(regex, function (match, src) {
    return `<img src="${src}" onerror="this.style.display='none'">`
  })

  // Open links in a new tab or window
  html = html.replace(/<a/g, '<a target="_blank"')

  // Fix href attribute to absolute path
  html = html.replace(
    /<a([^>]+href=["'])(?!https?:\/\/)([^"'>]+)/g,
    function (match, prefix, path) {
      var absolutePath = url + '/' + path
      return '<a' + prefix + absolutePath
    }
  )

  markdownContent.innerHTML = html

  // Append Markdown content element to modal content area
  modalContent.appendChild(markdownContent)

  // Append modal content area to modal element
  modal.appendChild(modalContent)

  // Append modal element to the page
  if (!document.querySelector('#mix-modal')) {
    document.body.appendChild(div)
  }
}

app.registerExtension({
  name: 'Comfy.Mixlab.ui',
  init () {
    LGraphCanvas.prototype.helpAboutNode = async function (node) {
      nodesMap =
        nodesMap && Object.keys(nodesMap).length > 0
          ? nodesMap
          : await getCustomnodeMappings('url')

      console.log(node, nodesMap, nodesMap[node.type])
      let repo = nodesMap[node.type]
      if (repo) {
        let markdown = await fetchReadmeContent(repo.url)
        console.log(markdown)

        createModal(repo.url, `# [${repo.title}](${repo.url})<br>${markdown}`)
      }
    }

    const getNodeMenuOptions = LGraphCanvas.prototype.getNodeMenuOptions // store the existing method
    LGraphCanvas.prototype.getNodeMenuOptions = function (node) {
      // replace it
      const options = getNodeMenuOptions.apply(this, arguments) // start by calling the stored one
      node.setDirtyCanvas(true, true) // force a redraw of (foreground, background)
      // options.splice(
      //   options.length - 1,
      //   0, // splice a new option in at the end
      //   {
      //     content: '♾️Mixlab', // with a name
      //     callback: () => {
      //       LGraphCanvas.prototype.helpAboutNode(node)
      //     } // and the callback
      //   },
      //   null // a divider
      // )
      return [
        {
          content: 'Help ♾️Mixlab', // with a name
          callback: () => {
            LGraphCanvas.prototype.helpAboutNode(node)
          } // and the callback
        },
        null,
        ...options
      ] // and return the options
    }
  },
  async setup () {
    const original_getCanvasMenuOptions = app.canvas.getCanvasMenuOptions // save the original function
    app.canvas.getCanvasMenuOptions = function () {
      const options = original_getCanvasMenuOptions.apply(this, arguments) // call the original function
      options.push(null) // divider
      options.push({
        content: `Help ♾️Mixlab`,
        disabled: false, // or a function determining whether to disable
        callback: async () => {
          nodesMap =
            nodesMap && Object.keys(nodesMap).length > 0
              ? nodesMap
              : await getCustomnodeMappings('url')

          const nodesDiv = document.createDocumentFragment()
          const nodes = (await app.graphToPrompt()).output

          // console.log('[Mixlab]', 'loaded graph node: ', app)
          let div =
            document.querySelector('#mixlab_find_the_node') ||
            document.createElement('div')
          div.id = 'mixlab_find_the_node'
          div.style = `
          flex-direction: column;
    align-items: end;
    display:flex;position: absolute; 
    top: 50px; left: 50px; width: 200px; 
    color: var(--descrip-text);
    background-color: var(--comfy-menu-bg);
     padding: 10px; 
     border: 1px solid black;z-index: 999999999;padding-top: 0;`

          div.innerHTML = ''

          let btn = document.createElement('div')
          btn.style=`display: flex;
          width: calc(100% - 24px);
          justify-content: space-between;
          align-items: center;
          padding: 0 12px;
          height: 32px;`
          let btnB = document.createElement('button')
          let textB = document.createElement('p')
          btn.appendChild(textB)
          btn.appendChild(btnB)
          textB.innerText = `find the node`

          btnB.style = `float: right; border: none; color: var(--input-text);
          background-color: var(--comfy-input-bg); border-color: var(--border-color);cursor: pointer;`
          btnB.addEventListener('click', () => {
            div.style.display = 'none'
          })
          btnB.innerText = 'X'

          // 悬浮框拖动事件
          div.addEventListener('mousedown', function (e) {
            var startX = e.clientX
            var startY = e.clientY
            var offsetX = div.offsetLeft
            var offsetY = div.offsetTop

            function moveBox (e) {
              var newX = e.clientX
              var newY = e.clientY
              var deltaX = newX - startX
              var deltaY = newY - startY
              div.style.left = offsetX + deltaX + 'px'
              div.style.top = offsetY + deltaY + 'px'
            }

            function stopMoving () {
              document.removeEventListener('mousemove', moveBox)
              document.removeEventListener('mouseup', stopMoving)
            }

            document.addEventListener('mousemove', moveBox)
            document.addEventListener('mouseup', stopMoving)
          })

          div.appendChild(btn)

          const updateNodes = (ns, nd) => {
            for (let nodeId in ns) {
              let n = ns[nodeId].class_type
              const { url, title } = nodesMap[n]
              let d = document.createElement('button')
              d.style = `text-align: left;margin:6px;color: var(--input-text);
              background-color: var(--comfy-input-bg); border-color: var(--border-color);cursor: pointer;`
              d.addEventListener('click', () => {
                const node = app.graph.getNodeById(nodeId)
                if (!node) return
                app.canvas.centerOnNode(node)
                app.canvas.setZoom(1)
              })
              d.addEventListener('mouseover', async () => {
                console.log('mouseover')
                let n = (await app.graphToPrompt()).output
                if (!deepEqual(n, ns)) {
                  nd.innerHTML = ''
                  updateNodes(n, nd)
                }
              })

              d.innerHTML = `
              <span>${'#' + nodeId} ${n}</span>
              <a href="${url}" target="_blank" style="text-decoration: none;">🔗</a>
              `
              d.title = title

              nd.appendChild(d)
            }
          }

          let nodesDivv = document.createElement('div')

          for (let nodeId in nodes) {
            let n = nodes[nodeId].class_type
            const { url, title } = nodesMap[n]
            let d = document.createElement('button')
            d.style = `text-align: left;margin:6px;color: var(--input-text);
            background-color: var(--comfy-input-bg); border-color: var(--border-color);cursor: pointer;`
            d.addEventListener('click', () => {
              const node = app.graph.getNodeById(nodeId)
              if (!node) return
              app.canvas.centerOnNode(node)
              app.canvas.setZoom(1)
            })
            d.addEventListener('mouseover', async () => {
              console.log('mouseover')
              let n = (await app.graphToPrompt()).output
              if (!deepEqual(n, nodes)) {
                nodesDivv.innerHTML = ''
                updateNodes(n, nodesDivv)
              }
            })

            d.innerHTML = `
            <span>${'#' + nodeId} ${n}</span>
            <a href="${url}" target="_blank" style="text-decoration: none;">🔗</a>
            `
            d.title = title

            nodesDiv.appendChild(d)
          }

          nodesDivv.appendChild(nodesDiv)
          nodesDivv.style=`overflow: scroll;
          height: 70vh;width: 100%;`

          div.appendChild(nodesDivv)

          if (!document.querySelector('#mixlab_find_the_node'))
            document.body.appendChild(div)
        }
      })
      return options // return the menu options with your custom ones added
    }
  }
})
