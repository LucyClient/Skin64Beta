package net.lucybeyondme.skin64beta.mixin;

import net.minecraft.client.Minecraft;
import net.minecraft.client.texture.TextureManager;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Minecraft.class)
public class MinecraftMixin {
    private static final Logger LOGGER = LogManager.getLogger("Skin64Beta");

    @Shadow 
    public TextureManager textureManager;

    @Inject(at = @At("TAIL"), method = "init")
    private void skin64beta$runSelfTest(CallbackInfo ci) {
        LOGGER.info("Game initialized. Running temporary skin-detection self-test...");

        try {
            if (this.textureManager != null) {
                this.textureManager.getTextureId("/assets/skin64beta/textures/LucyBeyondMe-64x64.png");
                this.textureManager.getTextureId("/assets/skin64beta/textures/LucyBeyondMe-64x32.png");
                LOGGER.info("Self-test complete.");
            } else {
                LOGGER.warn("TextureManager was surprisingly null during self-test.");
            }
        } catch (Throwable t) {
            LOGGER.error("Self-test threw an exception:", t);
        }
    }
}
