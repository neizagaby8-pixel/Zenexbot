if data_code.startswith("getnum_srv_"):
        selected_service = data_code.split("_")[2]
        user_target_services[chat_id] = selected_service
        
        try:
            res = requests.get(f'{BASE_URL}/liveaccess', headers={'mauthapi': PANEL_API_KEY}, timeout=5).json()
            if res.get('meta', {}).get('code') == 200:
                services_list = res.get('data', {}).get('services', [])
                keyboard = []
                has_data = False
                
                for s_item in services_list:
                    sid = str(s_item.get('sid', '')).strip().upper()
                    if sid == selected_service:
                        ranges = s_item.get('ranges', [])
                        country_groups = {}
                        
                        for r_raw in ranges:
                            r_str = str(r_raw).replace("XXX", "").replace("xxx", "").strip()
                            flag, c_code, full_name = get_country_info_by_range_or_text(r_str, "")
                            display_name = f"{full_name} ({c_code})"
                            
                            if display_name not in country_groups:
                                country_groups[display_name] = {"flag": flag, "c_code": c_code, "ranges": []}
                            country_groups[display_name]["ranges"].append(r_str)
                        
                        sorted_countries = sorted(country_groups.items(), key=lambda x: len(x[1]["ranges"]), reverse=True)
                        
                        for c_name, info in sorted_countries:
                            total_otp = len(info["ranges"])
                            if total_otp < 3:
                                continue
                            
                            btn_text = f"{info['flag']} {c_name} - {total_otp} OTP [HIGH 🟢]"
                            callback_val = f"cnt_{selected_service}_{info['c_code']}"
                            
                            keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_val)])
                            has_data = True
                        break
                
                if not has_data:
                    await query.edit_message_text(f"📭 **No High Traffic ranges available for {selected_service} right now.**", parse_mode="Markdown")
                    return
                
                keyboard.append([InlineKeyboardButton("Close", callback_data="close_menu")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"📱 **Select Country / High Traffic Range**\n📘 Service: `{selected_service}`\n\n👇 Choose a country below to view available high ranges:", 
                    parse_mode="Markdown", 
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text("❌ **Failed to load traffic ranges.**", parse_mode="Markdown")
        except Exception as e:
            await query.edit_message_text(f"⚠️ **Error:** `{e}`", parse_mode="Markdown")
        return
