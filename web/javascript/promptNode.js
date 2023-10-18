import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from "../../../scripts/widgets.js";


// 和python实现一样
function run(mutable_prompt, immutable_prompt) {
  // Split the text into an array of words
  const words1 = mutable_prompt.split("\n");
  
  // Split the text into an array of words
  const words2 = immutable_prompt.split("\n");
  
  const prompts = [];
  for (let i = 0; i < words1.length; i++) {
      words1[i]=words1[i].trim()
      for (let j = 0; j < words2.length; j++) {
          words2[j]=words2[j].trim()
          if(words2[j]&& words1[i]){
            prompts.push(words2[j].replaceAll('``', words1[i]));
          }
      }
  }
  
  return prompts;
}

// 更新ui，计算prompt的组合结果
const updateUI=(node)=>{
  const mutable_prompt_w = node.widgets.filter((w) => w.name === "mutable_prompt")[0];
        mutable_prompt_w.inputEl.title='Enter keywords, one per line'
        const immutable_prompt_w = node.widgets.filter((w) => w.name === "immutable_prompt")[0];
        immutable_prompt_w.inputEl.title='Enter prompts, one per line, variables represented by ``'

        const max_count = node.widgets.filter((w) => w.name === "max_count")[0];
        let prompts=run(mutable_prompt_w.value,immutable_prompt_w.value);

        prompts=prompts.slice(0,max_count.value);
        
        max_count.value=prompts.length;

        // 如果已经存在,删除
        const pos = node.widgets.findIndex((w) => w.name === "prompts");
				if (pos !== -1) {
					for (let i = pos; i < node.widgets.length; i++) {
						node.widgets[i].onRemove?.();
					}
				}

        // 动态添加
        const w = ComfyWidgets.STRING(node, "prompts", ["STRING", { multiline: true }], app).widget;
              w.inputEl.readOnly = true;
              w.inputEl.style.opacity = 0.6;
              w.value = prompts.join('\n');
              w.inputEl.title=`Total of ${prompts.length} prompts`;
        
        // node.widgets.length = 4;
        node.onResize?.(node.size);
}


const node = {
    name: 'RandomPrompt',
    async setup(a){
      console.log('#setup',app.graph._nodes )
      for (const node of app.graph._nodes) {
        if(node.comfyClass==='RandomPrompt'){
          updateUI(node)
        }
      }
    },
    async nodeCreated(node){
      
      if(node.comfyClass==='RandomPrompt'){
        updateUI(node)
      }
    },
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        
      // 注册节点前，可以修改节点的数据
      // 可以获取得到其他节点数据

        // 汉化
        // app.graph._nodes // title ='123' 
        
		if (nodeData.name === "RandomPrompt") {
      
			const onExecuted = nodeType.prototype.onExecuted;
			nodeType.prototype.onExecuted = function (message) {
				const r = onExecuted?.apply?.(this, arguments);
        console.log('#RandomPrompt', this.widgets)
				const pos = this.widgets.findIndex((w) => w.name === "prompts");
				if (pos !== -1) {
					for (let i = pos; i < this.widgets.length; i++) {
						this.widgets[i].onRemove?.();
					}
					// this.widgets.length = 4;
				}

        let prompts=message.prompts.join('\n');
			 
        const w = ComfyWidgets["STRING"](this, "prompts", ["STRING", { multiline: true }], app).widget;
					w.inputEl.readOnly = true;
					w.inputEl.style.opacity = 0.6;
					w.value = prompts;

				this.onResize?.(this.size);

				return r;
			};
		} 


    }
}

app.registerExtension(node)
